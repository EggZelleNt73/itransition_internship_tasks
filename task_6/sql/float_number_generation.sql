-- Stored Procedure for Uniform Float Generation
CREATE OR REPLACE PROCEDURE faker.proc_get_random_float(
    IN seed_str TEXT, 
    INOUT result DOUBLE PRECISION
)
AS $$
DECLARE
    hash_hex TEXT;
    big_val NUMERIC;
BEGIN
    hash_hex := substring(encode(digest(seed_str, 'sha256'), 'hex') from 1 for 14);
    big_val := ('x' || hash_hex)::bit(56)::bigint::numeric;
    result := big_val / 72057594037927936.0; 
END;
$$ LANGUAGE plpgsql;

-- Procedure for Box-Muller Normal Distribution
CREATE OR REPLACE PROCEDURE faker.proc_get_normal_float(
    IN seed_str TEXT, 
    IN mean DOUBLE PRECISION, 
    IN stddev DOUBLE PRECISION,
    INOUT result DOUBLE PRECISION
)
AS $$
DECLARE
    u1 DOUBLE PRECISION := 0.0;
    u2 DOUBLE PRECISION := 0.0;
    z0 DOUBLE PRECISION;
BEGIN
    -- Calling another stored procedure procedurally
    CALL faker.proc_get_random_float(seed_str || '_u1', u1);
    CALL faker.proc_get_random_float(seed_str || '_u2', u2);
    
    IF u1 = 0.0 THEN u1 := 0.0000001; END IF;
    
    z0 := sqrt(-2.0 * log(u1)) * cos(2.0 * pi() * u2);
    result := (z0 * stddev) + mean;
END;
$$ LANGUAGE plpgsql;