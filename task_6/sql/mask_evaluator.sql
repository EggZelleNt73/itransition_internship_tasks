-- Stored Procedure for Evaluating Dynamic Mask Fields (e.g., Zip Codes)
CREATE OR REPLACE PROCEDURE faker.proc_evaluate_mask(
    IN seed_str TEXT, 
    IN mask TEXT,
    INOUT mask_result TEXT
)
AS $$
DECLARE
    digit_val DOUBLE PRECISION;
    i INT;
    ch CHAR;
BEGIN
    mask_result := '';
    FOR i IN 1..length(mask) LOOP
        ch := substring(mask from i for 1);
        IF ch = '#' THEN
            CALL faker.proc_get_random_float(seed_str || '_m_' || i, digit_val);
            mask_result := mask_result || floor(digit_val * 10)::TEXT;
        ELSE
            mask_result := mask_result || ch;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;