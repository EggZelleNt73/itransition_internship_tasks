-- Stored Procedure for Spherical Geolocation Coordinates
CREATE OR REPLACE PROCEDURE faker.proc_get_spherical_coordinates(
    IN seed_str TEXT, 
    INOUT latitude DOUBLE PRECISION, 
    INOUT longitude DOUBLE PRECISION
)
AS $$
DECLARE
    u1 DOUBLE PRECISION := 0.0;
    u2 DOUBLE PRECISION := 0.0;
BEGIN
    CALL faker.proc_get_random_float(seed_str || '_lon', u1);
    CALL faker.proc_get_random_float(seed_str || '_lat', u2);
    
    longitude := (u1 * 360.0) - 180.0;
    latitude := degrees(asin(2.0 * u2 - 1.0));
END;
$$ LANGUAGE plpgsql;