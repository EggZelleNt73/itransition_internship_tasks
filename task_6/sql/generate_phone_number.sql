-- Stored Procedure for Localized Random Phone Creation
CREATE OR REPLACE PROCEDURE faker.proc_generate_phone(
    IN seed_str TEXT, 
    IN locale_str CHAR(3),
    INOUT phone_result TEXT
)
AS $$
DECLARE
    rand_val DOUBLE PRECISION := 0.0;
    raw_pattern TEXT;
    digit_val DOUBLE PRECISION;
    i INT;
    ch CHAR;
BEGIN
    CALL faker.proc_get_random_float(seed_str, rand_val);
    phone_result := '';
    
    IF locale_str = 'ENG' THEN
        raw_pattern := CASE 
            WHEN rand_val < 0.33 THEN '(###) ###-####'
            WHEN rand_val < 0.66 THEN '###-###-####'
            ELSE '+1 ### ### ####'
        END;
    ELSIF locale_str = 'DEU' THEN
        raw_pattern := CASE 
            WHEN rand_val < 0.33 THEN '+49 #### ######'
            WHEN rand_val < 0.66 THEN '0#### #######'
            ELSE '+49 (0) ### #######'
        END;
    ELSE
        raw_pattern := '##########';
    END IF;

    FOR i IN 1..length(raw_pattern) LOOP
        ch := substring(raw_pattern from i for 1);
        IF ch = '#' THEN
            CALL faker.proc_get_random_float(seed_str || '_p_' || i, digit_val);
            phone_result := phone_result || floor(digit_val * 10)::TEXT;
        ELSE
            phone_result := phone_result || ch;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;