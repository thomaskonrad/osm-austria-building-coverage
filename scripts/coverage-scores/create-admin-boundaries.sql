-- Make sure you install the PostGIS and hstore extensions before running this script!

-- Drop and recreate tables
drop table austria_admin_boundaries;

create table austria_admin_boundaries
(
    id serial not null,
    admin_level integer,
    name text,
    abbreviation text,
    way geometry,
    bbox geometry,
    full_tiles integer[][],
    partial_tiles integer[][],
    way_area real,
    gkz text,
    color text,
    parent integer,
    CONSTRAINT austria_admin_boundaries_pk_id PRIMARY KEY (id)
);

drop table if exists austria_building_coverage;

create table austria_building_coverage
(
    id serial not null,
    municipality_id integer not null,
    timestamp timestamptz(0) not null,
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
update austria_admin_boundaries set gkz = '60202' where name = 'St. Leonhard';
update austria_admin_boundaries set gkz = '60203' where name = 'Geidorf';
update austria_admin_boundaries set gkz = '60204' where name = 'Lend (Graz)';
update austria_admin_boundaries set gkz = '60205' where name = 'Gries';
update austria_admin_boundaries set gkz = '60206' where name = 'Jakomini';
update austria_admin_boundaries set gkz = '60207' where name = 'Liebenau (Graz)';
update austria_admin_boundaries set gkz = '60208' where name = 'St. Peter';
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

CREATE INDEX idx_austria_building_coverage_municipality_id -- This one is really important
ON austria_building_coverage (municipality_id);

CREATE INDEX idx_austria_building_coverage_timestamp
ON austria_building_coverage (timestamp);

-- Create simplified admin polygons

-- Drop views first
drop materialized view if exists coverage_boundary;
drop materialized view if exists coverage_score_base;

drop table if exists simplified_polygon;

create table simplified_polygon
(
  id int not null,
  admin_level int not null,
  polygon text,
  bbox text
);

insert into simplified_polygon(id, admin_level, polygon, bbox)

select b.gkz::int as id, b.admin_level,
ST_AsGeoJSON(ST_Transform(ST_Collect(ST_Simplify(b.way, 100)), 4326)) as polygon,
ST_AsGeoJSON(ST_Transform(ST_Envelope(ST_Collect(ST_Simplify(b.way, 100))), 4326)) as bbox
from austria_admin_boundaries b
where b.admin_level = 3
group by b.gkz, b.admin_level

union all

select b.gkz::int as id, b.admin_level,
ST_AsGeoJSON(ST_Transform(ST_Collect(ST_Simplify(b.way, 500)), 4326)) as polygon,
ST_AsGeoJSON(ST_Transform(ST_Envelope(ST_Collect(ST_Simplify(b.way, 500))), 4326)) as bbox
from austria_admin_boundaries b
where b.admin_level = 2
group by b.gkz, b.admin_level

union all

select b.gkz::int as id, b.admin_level,
ST_AsGeoJSON(ST_Transform(ST_Collect(ST_Simplify(b.way, 1000)), 4326)) as polygon,
ST_AsGeoJSON(ST_Transform(ST_Envelope(ST_Collect(ST_Simplify(b.way, 1000))), 4326)) as bbox
from austria_admin_boundaries b
where b.admin_level = 1
group by b.gkz, b.admin_level

union all

select 0::int as id, 0 as admin_level,
ST_AsGeoJSON(ST_Transform(ST_Collect(ST_Simplify(p.way, 1500)), 4326)) as polygon,
ST_AsGeoJSON(ST_Transform(ST_Envelope(ST_Collect(ST_Simplify(p.way, 1500))), 4326)) as bbox
from planet_osm_polygon p
where p.admin_level = '2' and p.name='Österreich'
group by id;

-- Base view
create materialized view coverage_score_base as
select b.gkz::int as gkz, b.name as name, p.gkz::int as district_id,
  max(c_current.timestamp) as latest_timestamp,
  min(c_original.timestamp) as oldest_timestamp,
  sum(c_current.total_pixels) as total_pixels,
  sum(c_current.covered_basemap_pixels) as covered_basemap_pixels,
  sum(c_current.uncovered_basemap_pixels) as uncovered_basemap_pixels,
  sum(c_original.covered_basemap_pixels) as covered_basemap_pixels_original,
  sum(c_original.uncovered_basemap_pixels) as uncovered_basemap_pixels_original
from austria_building_coverage c_original,
  austria_building_coverage c_current
left join austria_admin_boundaries b on (c_current.municipality_id = b.id)
left join austria_admin_boundaries p on (b.parent = p.id)
where c_current.timestamp = (
  select max(timestamp) from austria_building_coverage c1 -- The newest timestamp
  where c_current.municipality_id = c1.municipality_id)
and c_original.municipality_id = b.id
and c_original.timestamp = (
  select min(timestamp) from austria_building_coverage c2
  where c_original.municipality_id = c2.municipality_id
)
group by b.gkz, b.name, p.gkz;

-- Coverage boundary view
create materialized view coverage_boundary as

-- Municipalities
select csb.gkz as id, 3::int as admin_level, csb.name,
  rank() over(order by (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0)  desc) as rank,
  csb.district_id as parent_id,
  csb.latest_timestamp,
  csb.oldest_timestamp,
  sum(csb.total_pixels) as total_pixels,
  sum(csb.covered_basemap_pixels) as covered_basemap_pixels,
  sum(csb.uncovered_basemap_pixels) as uncovered_basemap_pixels,
  (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0) as coverage,
  (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0) as original_coverage,
  (
    (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0)
    -
    (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0)
  ) as total_coverage_gain,
  s.polygon, s.bbox
from coverage_score_base csb,
  simplified_polygon s
where csb.gkz = s.id and s.admin_level = 3
group by csb.gkz, csb.name, csb.district_id, csb.latest_timestamp, csb.oldest_timestamp, s.polygon, s.bbox


union all

-- Districts
select b.gkz::int as id, 2::int as admin_level, b.name as name,
  rank() over(order by (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0)  desc) as rank,
  p.gkz::int as parent_id,
  max(csb.latest_timestamp) as latest_timestamp,
  min(csb.oldest_timestamp) as oldest_timestamp,
  sum(csb.total_pixels) as total_pixels,
  sum(csb.covered_basemap_pixels) as covered_basemap_pixels,
  sum(csb.uncovered_basemap_pixels) as uncovered_basemap_pixels,
  (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0) as coverage,
  (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0) as original_coverage,
  (
    (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0)
    -
    (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0)
  ) as total_coverage_gain,
  s.polygon, s.bbox
from simplified_polygon s,
  austria_admin_boundaries b
  left join austria_admin_boundaries p on (b.parent = p.id)
  left join coverage_score_base csb on (csb.district_id = b.gkz::int)
where b.admin_level = 2
  and b.gkz::int = s.id and s.admin_level = 2
group by b.gkz::int, b.name, p.gkz, s.polygon, s.bbox

union all

-- States
select state.gkz::int as id, 1::int as admin_level, state.name,
  rank() over(order by (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0)  desc) as rank,
  0::int as parent_id,
  max(csb.latest_timestamp) as latest_timestamp,
  min(csb.oldest_timestamp) as oldest_timestamp,
  sum(csb.total_pixels) as total_pixels,
  sum(csb.covered_basemap_pixels) as covered_basemap_pixels,
  sum(csb.uncovered_basemap_pixels) as uncovered_basemap_pixels,
  (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0) as coverage,
  (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0) as original_coverage,
  (
    (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0)
    -
    (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0)
  ) as total_coverage_gain,
  s.polygon, s.bbox
from simplified_polygon s,
  austria_admin_boundaries state
  left join austria_admin_boundaries district on (district.parent = state.id)
  left join coverage_score_base csb on (csb.district_id = district.gkz::int)
where state.admin_level = 1
  and state.gkz::int = s.id and s.admin_level = 1
group by state.gkz, state.name, s.polygon, s.bbox

union all

-- Countries
select 0 as id, 0::int as admin_level, 'Österreich'::text as name, 1::int as rank, null as parent_id,
  max(csb.latest_timestamp) as latest_timestamp,
  min(csb.oldest_timestamp) as oldest_timestamp,
  sum(csb.total_pixels) as total_pixels,
  sum(csb.covered_basemap_pixels) as covered_basemap_pixels,
  sum(csb.uncovered_basemap_pixels) as uncovered_basemap_pixels,
  (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0) as coverage,
  (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0) as original_coverage,
  (
    (sum(csb.covered_basemap_pixels)::float / (sum(csb.covered_basemap_pixels) + sum(csb.uncovered_basemap_pixels)) * 100.0)
    -
    (sum(csb.covered_basemap_pixels_original)::float / (sum(csb.covered_basemap_pixels_original) + sum(csb.uncovered_basemap_pixels_original)) * 100.0)
  ) as total_coverage_gain,
  s.polygon, s.bbox
from simplified_polygon s,
  coverage_score_base csb
where s.id = 0 and s.admin_level = 0
group by s.polygon, s.bbox;
