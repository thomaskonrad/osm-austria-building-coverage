-- This SQL script takes only the newest coverage scores per municipality, inserts them into a temporary table,
-- truncates the coverage score table and inserts the newest scores. The current timestamp is taken as the coverage
-- timestamp. This script is used to throw away all old scores and start from today.
drop table if exists austria_building_coverage_temp;

create table austria_building_coverage_temp
(
    id serial not null,
    municipality_id integer not null,
    timestamp timestamptz(0) not null,
    total_pixels integer not null,
    covered_basemap_pixels integer not null,
    uncovered_basemap_pixels integer not null
);

insert into austria_building_coverage_temp (municipality_id, timestamp, total_pixels, covered_basemap_pixels, uncovered_basemap_pixels)
(
  select municipality_id, current_timestamp, total_pixels, covered_basemap_pixels, uncovered_basemap_pixels
  from austria_building_coverage c
  where c.timestamp = (
    select max(timestamp) from austria_building_coverage c1 -- The newest timestamp
    where c.municipality_id = c1.municipality_id)
);

truncate table austria_building_coverage;

insert into austria_building_coverage (select * from austria_building_coverage_temp);

drop table austria_building_coverage_temp;

refresh materialized view coverage_score_base;
refresh materialized view coverage_boundary;
