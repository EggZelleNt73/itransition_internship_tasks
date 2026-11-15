CREATE OR REPLACE PROCEDURE faker.proc_generate_user_batch(
    IN p_base_seed INT,
    IN p_locale CHAR(3),
    IN p_batch_size INT,
    IN p_batch_offset INT,
    INOUT p_result_cursor REFCURSOR
)
AS $$
DECLARE
    -- Ceilings
    v_total_fn_m INT; v_total_fn_f INT; v_total_ln INT; v_total_st INT; v_total_ct INT;
    
    -- Loop Variables
    i INT;
    v_row_seed TEXT;
    
    -- Intermediate Random Value Drops
    v_gender_roll DOUBLE PRECISION; v_fn_roll DOUBLE PRECISION; v_ln_roll DOUBLE PRECISION;
    v_st_roll DOUBLE PRECISION; v_ct_roll DOUBLE PRECISION; v_title_roll DOUBLE PRECISION;
    v_middle_roll DOUBLE PRECISION; v_addr_roll DOUBLE PRECISION; v_eye_roll DOUBLE PRECISION;
    v_str_num_roll DOUBLE PRECISION; v_apt_roll DOUBLE PRECISION; v_em_roll DOUBLE PRECISION;
    
    -- Resolved Record Items
    v_gender CHAR(1); v_fn_seq INT; v_ln_seq INT; v_st_seq INT; v_ct_seq INT;
    v_fn_text TEXT; v_ln_text TEXT; v_st_text TEXT; v_ct_text TEXT; v_state_text TEXT; v_zip_mask TEXT;
    
    -- Complex Output Calculated Targets
    v_final_name TEXT; v_final_addr TEXT; v_lat DOUBLE PRECISION; v_lon DOUBLE PRECISION;
    v_height DOUBLE PRECISION; v_weight DOUBLE PRECISION; v_eye_color TEXT;
    v_phone TEXT; v_zip_eval TEXT;
BEGIN
    -- 1. Read lookup limits
    SELECT COALESCE(MAX(seq_id), 0) INTO v_total_fn_m FROM faker.lookup_first_names WHERE locale = p_locale AND gender = 'M';
    SELECT COALESCE(MAX(seq_id), 0) INTO v_total_fn_f FROM faker.lookup_first_names WHERE locale = p_locale AND gender = 'F';
    SELECT COALESCE(MAX(seq_id), 0) INTO v_total_ln FROM faker.lookup_last_names WHERE locale = p_locale;
    SELECT COALESCE(MAX(seq_id), 0) INTO v_total_st FROM faker.lookup_streets WHERE locale = p_locale;
    SELECT COALESCE(MAX(seq_id), 0) INTO v_total_ct FROM faker.lookup_cities WHERE locale = p_locale;

    IF v_total_ln = 0 OR v_total_st = 0 OR v_total_ct = 0 THEN
        RAISE EXCEPTION 'Lookup dataset completely unpopulated for target: %', p_locale;
    END IF;

    -- 2. Build local transactional scratch table
    DROP TABLE IF EXISTS temp_batch_output;
    CREATE TEMPORARY TABLE temp_batch_output (
        full_name TEXT, street_address TEXT, latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
        height_cm INT, weight_kg INT, eye_color VARCHAR(20), phone_number TEXT, email_address TEXT
    );

    -- 3. Execute row loop procedurally
    FOR i IN 0..(p_batch_size - 1) LOOP
        -- Define composite seed anchor string
        v_row_seed := p_base_seed::TEXT || '_' || p_locale || '_' || p_batch_offset::TEXT || '_' || i::TEXT;
        
        -- Execute assignments using procedure calls exclusively
        CALL faker.proc_get_random_float(v_row_seed || '_gender', v_gender_roll);
        v_gender := CASE WHEN v_gender_roll < 0.5 THEN 'M' ELSE 'F' END;
        
        CALL faker.proc_get_random_float(v_row_seed || '_fn_idx', v_fn_roll);
        v_fn_seq := (FLOOR(v_fn_roll * (CASE WHEN v_gender = 'M' THEN v_total_fn_m ELSE v_total_fn_f END)) + 1)::INT;
        
        CALL faker.proc_get_random_float(v_row_seed || '_ln_idx', v_ln_roll);
        v_ln_seq := (FLOOR(v_ln_roll * v_total_ln) + 1)::INT;
        
        CALL faker.proc_get_random_float(v_row_seed || '_st_idx', v_st_roll);
        v_st_seq := (FLOOR(v_st_roll * v_total_st) + 1)::INT;
        
        CALL faker.proc_get_random_float(v_row_seed || '_ct_idx', v_ct_roll);
        v_ct_seq := (FLOOR(v_ct_roll * v_total_ct) + 1)::INT;
        
        -- Pull data matches from tables into local procedural scope variables
        SELECT first_name INTO v_fn_text FROM faker.lookup_first_names WHERE locale = p_locale AND gender = v_gender AND seq_id = v_fn_seq;
        SELECT last_name INTO v_ln_text FROM faker.lookup_last_names WHERE locale = p_locale AND seq_id = v_ln_seq;
        SELECT street_name INTO v_st_text FROM faker.lookup_streets WHERE locale = p_locale AND seq_id = v_st_seq;
        SELECT city_name, state_or_region, postal_code_pattern INTO v_ct_text, v_state_text, v_zip_mask FROM faker.lookup_cities WHERE locale = p_locale AND seq_id = v_ct_seq;
        
        -- Evaluate layout variations
        CALL faker.proc_get_random_float(v_row_seed || '_v1', v_title_roll);
        CALL faker.proc_get_random_float(v_row_seed || '_v2', v_middle_roll);
        CALL faker.proc_get_random_float(v_row_seed || '_v3', v_addr_roll);
        
        v_final_name := CASE 
            WHEN v_title_roll < 0.15 THEN (CASE WHEN p_locale = 'DEU' THEN 'Dr. ' WHEN v_gender = 'M' THEN 'Mr. ' ELSE 'Ms. ' END)
            ELSE ''
        END || v_fn_text || CASE WHEN v_middle_roll < 0.20 THEN ' ' || substring(v_ln_text from 1 for 1) || '.' ELSE '' END || ' ' || v_ln_text;
        
        CALL faker.proc_evaluate_mask(v_row_seed || '_zip', v_zip_mask, v_zip_eval);
        CALL faker.proc_get_random_float(v_row_seed || '_str_num', v_str_num_roll);
        
        v_final_addr := CASE 
            WHEN p_locale = 'ENG' THEN 
                FLOOR(v_str_num_roll * 9999 + 1)::TEXT || ' ' || v_st_text || ', ' || v_ct_text || ', ' || v_state_text || ' ' || v_zip_eval
            ELSE 
                v_st_text || ' ' || FLOOR(v_str_num_roll * 150 + 1)::TEXT || ', ' || v_zip_eval || ' ' || v_ct_text
        END;
        
        -- Geolocation procedure execution
        CALL faker.proc_get_spherical_coordinates(v_row_seed || '_geo', v_lat, v_lon);
        
        -- Physical profile procedures execution
        CALL faker.proc_get_normal_float(v_row_seed || '_h', 175.0, 10.0, v_height);
        CALL faker.proc_get_normal_float(v_row_seed || '_w', 75.0, 15.0, v_weight);
        
        CALL faker.proc_get_random_float(v_row_seed || '_eye', v_eye_roll);
        v_eye_color := CASE 
            WHEN v_eye_roll < 0.45 THEN 'Brown' WHEN v_eye_roll < 0.75 THEN 'Blue' WHEN v_eye_roll < 0.90 THEN 'Hazel' ELSE 'Green'
        END;
        
        -- Phone generator execution
        CALL faker.proc_generate_phone(v_row_seed || '_phone', p_locale, v_phone);
        
        CALL faker.proc_get_random_float(v_row_seed || '_em_num', v_em_roll);
        
        -- Write final resolved row map to scratch space
        INSERT INTO temp_batch_output VALUES (
            v_final_name, v_final_addr, v_lat, v_lon, FLOOR(v_height)::INT, FLOOR(v_weight)::INT, 
            v_eye_color, v_phone, lower(v_fn_text || '.' || v_ln_text || FLOOR(v_em_roll * 89 + 10)::TEXT || CASE WHEN p_locale = 'DEU' THEN '@example.de' ELSE '@example.com' END)
        );
    END LOOP;

    -- 4. Stream data out through the cursor reference
    OPEN p_result_cursor FOR SELECT * FROM temp_batch_output;
END;
$$ LANGUAGE plpgsql;
