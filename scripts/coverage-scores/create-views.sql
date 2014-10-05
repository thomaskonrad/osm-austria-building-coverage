-- Create simplified admin polygons

-- Drop views first
drop materialized view if exists coverage_boundary;
drop materialized view if exists coverage_boundary_base;

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
create materialized view coverage_boundary_base as
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
from coverage_boundary_base csb,
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
  left join coverage_boundary_base csb on (csb.district_id = b.gkz::int)
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
  left join coverage_boundary_base csb on (csb.district_id = district.gkz::int)
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
  coverage_boundary_base csb
where s.id = 0 and s.admin_level = 0
group by s.polygon, s.bbox;



-- Materialized view with all coverage score entries
drop materialized view if exists coverage_score;
drop materialized view if exists coverage_change_date;
drop materialized view if exists coverage_score_base;
drop sequence coverage_score_id_seq;

create materialized view coverage_score_base as
select b.gkz::int as municipality_id, p.gkz::int as district_id, state.gkz::int as state_id,
  c_current.timestamp::date as date,
  max(c_current.total_pixels) as total_pixels, -- We take max() because we are grouping per day, not per timestamp
  max(c_current.covered_basemap_pixels) as covered_basemap_pixels,
  max(c_current.uncovered_basemap_pixels) as uncovered_basemap_pixels
from austria_building_coverage c_current
left join austria_admin_boundaries b on (c_current.municipality_id = b.id)
left join austria_admin_boundaries p on (b.parent = p.id)
left join austria_admin_boundaries state on (p.parent = state.id)
where c_current.municipality_id = b.id
group by b.gkz, p.gkz::int, state.gkz::int, c_current.timestamp::date;

-- Create indexes
CREATE INDEX idx_coverage_score_base_municipality_id ON coverage_score_base (municipality_id);
CREATE INDEX idx_coverage_score_base_district_id ON coverage_score_base (district_id);
CREATE INDEX idx_coverage_score_base_state_id ON coverage_score_base (state_id);
CREATE INDEX idx_coverage_score_base_date ON coverage_score_base (date);
CREATE INDEX idx_coverage_score_base_total_pixels ON coverage_score_base (total_pixels);
CREATE INDEX idx_coverage_score_base_covered_basemap_pixels ON coverage_score_base (covered_basemap_pixels);
CREATE INDEX idx_coverage_score_base_uncovered_basemap_pixels ON coverage_score_base (uncovered_basemap_pixels);

-- Change dates of each district
create materialized view coverage_change_date as

select district_id as id, 2 as admin_level, date
from coverage_score_base
group by district_id, date

union all

select state_id as id, 1 as admin_level, date
from coverage_score_base
group by state_id, date

union all

select 0 as id, 0 as admin_level, date
from coverage_score_base
group by date

order by id, date asc;

create sequence coverage_score_id_seq;

-- Coverage score view
create materialized view coverage_score as

-- Country
select nextval('coverage_score_id_seq') as id, c.id as coverage_boundary_id, c.date, (sum(m.covered_basemap_pixels)::float / (sum(m.covered_basemap_pixels) + sum(m.uncovered_basemap_pixels)) * 100.0) as coverage
from coverage_change_date c, coverage_score_base m
where c.admin_level = 0
and m.date = (
  select max(date) from coverage_score_base m2
  where m.municipality_id = m2.municipality_id
  and date <= c.date
)
group by c.id, c.date

union all

-- States
select nextval('coverage_score_id_seq') as id, s.id as coverage_boundary_id, s.date, (sum(m.covered_basemap_pixels)::float / (sum(m.covered_basemap_pixels) + sum(m.uncovered_basemap_pixels)) * 100.0) as coverage
from coverage_change_date s
left join coverage_score_base m on (m.state_id = s.id)
where s.admin_level = 1
and m.date = (
  select max(date) from coverage_score_base m2
  where m.municipality_id = m2.municipality_id
  and date <= s.date
)
group by s.id, s.date

union all

-- Districts
select nextval('coverage_score_id_seq') as id, d.id as coverage_boundary_id, d.date,
(sum(m.covered_basemap_pixels)::float / (sum(m.covered_basemap_pixels) + sum(m.uncovered_basemap_pixels)) * 100.0) as coverage
from coverage_change_date d
left join coverage_score_base m on (m.district_id = d.id)
where m.date = (
  select max(date) from coverage_score_base m2
  where m.municipality_id = m2.municipality_id
  and date <= d.date
)
group by d.id, d.date

union all

-- Municipalities
select nextval('coverage_score_id_seq') as id, municipality_id as coverage_boundary_id, date,
  (covered_basemap_pixels::float / (covered_basemap_pixels + uncovered_basemap_pixels) * 100.0) as coverage
from coverage_score_base

order by coverage_boundary_id, date asc;