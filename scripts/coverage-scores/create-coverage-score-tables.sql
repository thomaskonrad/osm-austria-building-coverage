DROP TABLE IF EXISTS austria_building_coverage;

CREATE TABLE austria_building_coverage
(
  id                       SERIAL         NOT NULL,
  boundary_id              INTEGER        NOT NULL,
  timestamp                TIMESTAMPTZ(0) NOT NULL,
  covered_basemap_pixels   INTEGER        NOT NULL,
  total_basemap_pixels     INTEGER        NOT NULL,
  coverage                 FLOAT          NOT NULL,
  CONSTRAINT austria_building_coverage_pk_id PRIMARY KEY (id)
);


CREATE INDEX idx_austria_building_coverage_municipality_id -- This one is really important
ON austria_building_coverage (boundary_id);

CREATE INDEX idx_austria_building_coverage_timestamp
ON austria_building_coverage (timestamp);
