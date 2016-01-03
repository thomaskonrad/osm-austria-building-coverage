-- Create covarage_boundary view.
drop materialized view if exists coverage_boundary;

create materialized view coverage_boundary as
select b.gkz::int as id, b.admin_level, b.name, b.abbreviation,
  rank() over (partition by b.admin_level order by coverage desc) as rank,
  parent.gkz::int as parent_id,
  (select max(c1.timestamp) from austria_building_coverage c1 where c1.boundary_id = b.id) as latest_timestamp,
  (select min(c1.timestamp) from austria_building_coverage c1 where c1.boundary_id = b.id) as oldest_timestamp,
  (
    select c1.coverage
    from austria_building_coverage c1
    where c1.boundary_id = b.id and timestamp =
      (select max(c1.timestamp) from austria_building_coverage c1 where c1.boundary_id = b.id)
  ) as coverage,
  (
    select c4.coverage
    from austria_building_coverage c4
    where c4.boundary_id = b.id and timestamp =
      (select min(c1.timestamp) from austria_building_coverage c1 where c1.boundary_id = b.id)
  ) as original_coverage,
  (
    (
      SELECT c1.coverage
      FROM austria_building_coverage c1
      WHERE c1.boundary_id = b.id AND timestamp =
                                      (SELECT max(c1.timestamp)
                                       FROM austria_building_coverage c1
                                       WHERE c1.boundary_id = b.id)
    )
    -
    (
    select c4.coverage
    from austria_building_coverage c4
    where c4.boundary_id = b.id and timestamp =
      (select min(c1.timestamp) from austria_building_coverage c1 where c1.boundary_id = b.id)
    )
  ) as total_coverage_gain,
  b.simplified_way_geojson as polygon,
  b.bbox_geojson as bbox
from austria_admin_boundaries b
  left join austria_admin_boundaries parent on (b.parent = parent.id)
  left join austria_building_coverage c on (c.boundary_id = b.id and c.timestamp = (select max(c1.timestamp) from austria_building_coverage c1 where c1.boundary_id = b.id))
;


-- Create coverage score view.
drop view if exists coverage_score;

create view coverage_score as
select c.id, b.gkz::int as coverage_boundary_id, c.timestamp::date as date, c.coverage
from austria_building_coverage c
  left join austria_admin_boundaries b on (c.boundary_id = b.id)
order by date asc;
