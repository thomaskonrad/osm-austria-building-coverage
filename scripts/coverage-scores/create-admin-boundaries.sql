-- Make sure you install the PostGIS, hstore, and pgcrypto extensions before running this script!
-- The script will take approximately 80 seconds to run.

-- Drop and recreate tables
drop table if exists austria_admin_boundaries;

create table austria_admin_boundaries
(
    id serial not null,
    admin_level integer,
    name text,
    abbreviation text,
    way geometry,
    simplified_way_geojson text,
    bbox geometry,
    bbox_geojson text,
    full_tiles integer[][],
    partial_tiles integer[][],
    way_area real,
    gkz text,
    color text,
    parent integer,
    CONSTRAINT austria_admin_boundaries_pk_id PRIMARY KEY (id)
);

-- Select Austrian federal states and insert them
insert into austria_admin_boundaries (admin_level, name, way, bbox, way_area, gkz)
(
    select 1 as admin_level, p.name, p.way, ST_Envelope(p.way) as bbox, p.way_area, r.tags::hstore->'ref:at:gkz' as gkz
    from planet_osm_polygon p, planet_osm_rels r
    where boundary='administrative' and admin_level='4'
    and r.tags::hstore ? 'ref:at:gkz'
    and (p.osm_id * -1) = r.id
    order by gkz
);

-- Set the Austrian federal state abbreviations according to ÖNORM A 1080
update austria_admin_boundaries set abbreviation='Bgld.' where name='Burgenland';
update austria_admin_boundaries set abbreviation='Ktn.' where name='Kärnten';
update austria_admin_boundaries set abbreviation='NÖ' where name='Niederösterreich';
update austria_admin_boundaries set abbreviation='OÖ' where name='Oberösterreich';
update austria_admin_boundaries set abbreviation='Sbg.' where name='Salzburg';
update austria_admin_boundaries set abbreviation='Stmk.' where name='Steiermark';
update austria_admin_boundaries set abbreviation='T' where name='Tirol';
update austria_admin_boundaries set abbreviation='Vbg.' where name='Vorarlberg';
update austria_admin_boundaries set abbreviation='W' where name='Wien';

-- Update GKZ of Vienna (which is both a federal state and a municipality)
update austria_admin_boundaries set gkz='9' where admin_level = 1 and gkz='9,90001';

-- Insert districts
insert into austria_admin_boundaries (admin_level, name, abbreviation, way, bbox, way_area, gkz, parent)
(
    select 2 as admin_level, p.name, r.tags::hstore->'ref', p.way, ST_Envelope(p.way) as bbox, p.way_area, r.tags::hstore->'ref:at:gkz', parent.id
    from planet_osm_rels r, planet_osm_polygon p
    left join austria_admin_boundaries parent on (parent.admin_level=1 and ST_Within(p.way, parent.way))
    where boundary='administrative'
    and
        (
            p.admin_level='6'
            or (p.admin_level='4' and p.name='Wien')
        )
    and r.tags::hstore ? 'ref:at:gkz'
    and (p.osm_id * -1) = r.id
    order by gkz
);

-- Update GKZ of Vienna (which is both a federal state and a municipality)
update austria_admin_boundaries set gkz='900' where admin_level = 2 and gkz='9,90001';
update austria_admin_boundaries set gkz='10101' where admin_level = 3 and name='Eisenstadt (Stadt)';
update austria_admin_boundaries set gkz='10201' where admin_level = 3 and name='Rust';

-- Insert all municipalities (takes 55 seconds on my machine)
insert into austria_admin_boundaries (admin_level, name, way, bbox, way_area, gkz, parent)
(
    select 3 as admin_level, p.name, p.way, ST_Envelope(p.way) as bbox, p.way_area, r.tags::hstore->'ref:at:gkz' as gkz, parent.id
    from planet_osm_rels r,
    planet_osm_polygon p
    left join austria_admin_boundaries parent on (parent.admin_level=2 and ST_Within(p.way, parent.way))
    where p.boundary='administrative'
    and
        (
            p.admin_level='8'
            or (p.admin_level='6' and p.name='Rust') -- Statutarstadt
            or (p.admin_level='6' and p.name='Eisenstadt (Stadt)') -- Statutarstadt
        )
    and p.name != 'Graz'
    and (p.osm_id * -1) = r.id
    and r.tags::hstore ? 'ref:at:gkz'
    and r.tags::hstore ? 'name'
    and (
        (not r.tags::hstore ? 'start_date' or (r.tags::hstore->'start_date')::date < now())
        and
        (not r.tags::hstore ? 'end_date' or (r.tags::hstore->'end_date')::date > now())
    )
    order by gkz
);

update austria_admin_boundaries set gkz='61214' where name = 'Großsölk';

-- Insert city districts / municipalities as municipalities
insert into austria_admin_boundaries (admin_level, name, way, bbox, way_area, gkz, parent)
(
    select 3 as admin_level, p.name, p.way, ST_Envelope(p.way) as bbox, p.way_area, r.tags::hstore->'ref:at:gkz' as gkz, parent.id
    from planet_osm_rels r,
    planet_osm_polygon p
    left join austria_admin_boundaries parent on (parent.admin_level=2 and ST_Within(p.way, parent.way))
    where p.boundary='administrative' and p.admin_level='9'
    and (p.osm_id * -1) = r.id
    and parent.name in ('Wien', 'Graz') -- Only these cities have complete district polygons
    order by gkz
);

-- Remove leading "Gemeinde", "Markgemeinde", "Stadtgemeinde" and "Bezirk" strings
update austria_admin_boundaries
set name = substring(name from 10 for length(name) - 9)
where name like 'Gemeinde %';

update austria_admin_boundaries
set name = substring(name from 15 for length(name) - 14)
where name like 'Marktgemeinde %';

update austria_admin_boundaries
set name = substring(name from 15 for length(name) - 14)
where name like 'Stadtgemeinde %';

update austria_admin_boundaries
set name = substring(name from 8 for length(name) - 7)
where name like 'Bezirk %';

-- Append the city or district name in parenthesis where the municipality name is ambiguous
update austria_admin_boundaries m
set name = m.name || ' (' || p.name || ')'
from austria_admin_boundaries p
where m.parent = p.id and
m.name in ('Innere Stadt', 'Liebenau', 'Mühldorf', 'Lend', 'Warth', 'Krumbach');

-- Give the city districts of Graz an "artificial" GKZ
update austria_admin_boundaries set gkz = '60201' where name = 'Innere Stadt (Graz)';
update austria_admin_boundaries set gkz = '60202' where name = 'Sankt Leonhard';
update austria_admin_boundaries set gkz = '60203' where name = 'Geidorf';
update austria_admin_boundaries set gkz = '60204' where name = 'Lend (Graz)';
update austria_admin_boundaries set gkz = '60205' where name = 'Gries';
update austria_admin_boundaries set gkz = '60206' where name = 'Jakomini';
update austria_admin_boundaries set gkz = '60207' where name = 'Liebenau (Graz)';
update austria_admin_boundaries set gkz = '60208' where name = 'Sankt Peter';
update austria_admin_boundaries set gkz = '60209' where name = 'Waltendorf';
update austria_admin_boundaries set gkz = '60210' where name = 'Ries';
update austria_admin_boundaries set gkz = '60211' where name = 'Mariatrost';
update austria_admin_boundaries set gkz = '60212' where name = 'Andritz';
update austria_admin_boundaries set gkz = '60213' where name = 'Gösting';
update austria_admin_boundaries set gkz = '60214' where name = 'Eggenberg';
update austria_admin_boundaries set gkz = '60215' where name = 'Wetzelsdorf';
update austria_admin_boundaries set gkz = '60216' where name = 'Straßgang';
update austria_admin_boundaries set gkz = '60217' where name = 'Puntigam';

-- Set a (hopefully) different color for each boundary
update austria_admin_boundaries set color='#' || substring(encode(digest(name, 'sha256'), 'hex') from 1 for 6);

-- Create indexes
CREATE INDEX idx_austria_admin_boundaries_name
ON austria_admin_boundaries (name);

CREATE INDEX idx_austria_admin_boundaries_gkz
ON austria_admin_boundaries (gkz);

CREATE INDEX idx_austria_admin_boundaries_parent
ON austria_admin_boundaries (parent);

-- Create a simplified border polygons and bbox both as GeoJSON and update boundaries table.
update austria_admin_boundaries b
set simplified_way_geojson =
    (select ST_AsGeoJSON(ST_Transform(ST_Collect(ST_Simplify(b2.way, 100)), 4326))
     from austria_admin_boundaries b2
     where b.id = b2.id),
bbox_geojson =
    (select ST_AsGeoJSON(ST_Transform(ST_Envelope(ST_Collect(ST_Simplify(b3.way, 100))), 4326))
     from austria_admin_boundaries b3
     where b.id = b3.id);
