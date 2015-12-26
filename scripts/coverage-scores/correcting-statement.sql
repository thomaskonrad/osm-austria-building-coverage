-- Correcting statement. Issue this after the service has been running at least two days. The problem is that if a tile
-- is updated that is part of the municipality's tile set but does not affect the municipality, the timestamp of the
-- last coverage is simply updated. That may lead to the case where some municipalities do not have a
-- austria_building_coverage entry on the first day.
insert into austria_building_coverage (municipality_id, timestamp, total_pixels, covered_basemap_pixels, uncovered_basemap_pixels)
  select c.municipality_id, (select min(c3.timestamp) from austria_building_coverage c3), min(total_pixels), min(covered_basemap_pixels), max(uncovered_basemap_pixels)
  from austria_building_coverage c
  group by c.municipality_id
  having min(c.timestamp::date) > (select min(c2.timestamp::date) from austria_building_coverage c2)
  order by c.municipality_id;
