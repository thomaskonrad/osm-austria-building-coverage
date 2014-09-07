-- Drop and recreate table
drop table austria_admin_boundaries;

CREATE TABLE austria_admin_boundaries
(
  id serial not null,
  admin_level integer,
  name text,
  abbreviation text,
  way geometry,
  bbox geometry,
  tile_min_x_16 integer,
  tile_max_x_16 integer,
  tile_min_y_16 integer,
  tile_max_y_16 integer,
  way_area real,
  gkz text,
  color text,
  parent integer,
  CONSTRAINT austria_admin_boundaries_pk_id PRIMARY KEY (id)
);

drop table if exists austria_building_coverage;

CREATE TABLE austria_building_coverage
(
  id serial not null,
  municipality_id integer not null,
  capture_date date not null,
  total_pixels integer not null,
  covered_basemap_pixels integer not null,
  uncovered_basemap_pixels integer not null,
  CONSTRAINT austria_building_coverage_pk_id PRIMARY KEY (id)
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

-- Insert city districts / municipalities as municipalities
insert into austria_admin_boundaries (admin_level, name, way, bbox, way_area, gkz, parent)
(
    select 3 as admin_level, p.name, p.way, ST_Envelope(p.way) as bbox, p.way_area, r.tags::hstore->'ref:at:gkz' as gkz, parent.id
    from planet_osm_rels r,
    planet_osm_polygon p
    left join austria_admin_boundaries parent on (parent.admin_level=2 and ST_Within(p.way, parent.way))
    where p.boundary='administrative' and p.admin_level='9'
    and (p.osm_id * -1) = r.id
    and parent.name in ('Wien', 'Graz', 'Klagenfurt (Stadt)') -- Only these cities have complete district polygons
    order by gkz
);

-- Set a (hopefully) different color for each boundary
update austria_admin_boundaries set color='#'||substring(encode(digest(name, 'sha256'), 'hex') from 1 for 6);

-- Special cases: [DONE] Rust (Statutarstadt), [DONE] Neusiedl am See (split in two), [DONE] Eisenstadt,
-- [DONE] Naarn im Machlande (not here but in OSM), [DONE] Perg (not here but in OSM), [DONE] Kulm am Zirbitz (not in OSM)
-- [DONE] Kleinlobming (not in OSM), [DONE] Reisstraße (not here but in OSM), [DONE] Großsölk (not in OSM, Sölk?)
