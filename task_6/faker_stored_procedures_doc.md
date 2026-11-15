# Technical Documentation: SQL-Faker Engine Stored Procedures

This document provides a comprehensive overview of the `faker` schema database layer implemented inside **PostgreSQL (PL/pgSQL)**. 

The entire fake data generation pipeline is implemented **exclusively using stored procedures**. To fulfill project requirements, it avoids any dependency on external runtime code libraries for random sampling, formatting, or distribution math, making the database layer an independent, reproducible, and scalable generation engine.

---

## 1. Core Architecture & Reproducibility Matrix

### The Deterministic PRNG Strategy
Standard relational random operations (`RANDOM()`) are stateful and non-reproducible across transactional sessions. To guarantee absolute reproducibility across batch boundaries, this engine implements a **Cryptographic Hashing Pseudo-Random Number Generator (PRNG)**.

Every random choice is driven by a unique **composite position string seed**:
$$\text{Composite Seed} = \text{concat}(P\_Base\_Seed, '\_', P\_Locale, '\_', P\_Batch\_Offset, '\_', Row\_Index, '\_', Attribute\_Suffix)$$

The procedure passes this string through a `SHA-256` hashing function (`digest()` from the `pgcrypto` extension). The first 14 hexadecimal characters (56 bits of entropy) are extracted, converted into a bit string, cast to a numeric bigint, and divided by $2^{56} - 1$ ($72,057,594,037,927,936.0$). This maps every exact position deterministically to a floating-point value uniformly distributed in the range $[0.0, 1.0)$.

### High-Volume Index Optimization (O(1) Scaling)
To efficiently scale from **100,000 to 1,000,000 fake records**, traditional lookup patterns like `ORDER BY random() LIMIT 1` must be avoided because they require expensive full-table sequential scans.

Instead, this engine utilizes unified lookup tables containing a `seq_id` integer tracking field that increments continuously starting from 1 for every independent combination of `locale` (using `CHAR(3)` ISO codes) and `gender`. The generation procedures count the maximum `seq_id` boundaries for the active locale, multiply it by a deterministic uniform float, and perform a microsecond direct B-Tree index lookup:
```sql
WHERE locale = p_locale AND gender = v_gender AND seq_id = v_calculated_index
```
This reduces lookups to an O(1) time complexity, ensuring execution speeds remain lightning-fast and flat as datasets scale.

---

## 2. Stored Procedure Specifications

### 2.1 `faker.proc_get_random_float`
Generates a deterministic uniform pseudo-random floating-point value.

#### Arguments
*   `IN seed_str TEXT`: The distinct composite position text string representing the context of the generation.
*   `INOUT result DOUBLE PRECISION`: The reference variable populated with the resulting uniform float in the range $[0.0, 1.0)$.

#### Algorithm Mechanics
1. Appends the string to initialize an immutable state.
2. Computes the binary hash payload using `sha256`.
3. Isolates a slice of the hexadecimal string, bit-shifts it into a standard base-10 numerical register, and applies a scalar boundary filter to yield a number between `0` (inclusive) and `1` (exclusive).

---

### 2.2 `faker.proc_get_normal_float`
Generates a pseudo-random floating-point value conforming to a normal (Gaussian/bell-curve) distribution using the **Box-Muller Transform**.

#### Arguments
*   `IN seed_str TEXT`: The distinct composite position string anchor.
*   `IN mean DOUBLE PRECISION`: The average or center point of the bell curve (e.g., average height/weight).
*   `IN stddev DOUBLE PRECISION`: The standard deviation controlling the width/variance of the distribution curve.
*   `INOUT result DOUBLE PRECISION`: The reference variable populated with the transformed normal value.

#### Mathematical Algorithm
The Box-Muller transform converts two independent, uniformly distributed random variables ($U_1, U_2$) on the interval $[0, 1)$ into standard normally distributed random variables. 

To achieve this procedurally, the procedure derives two distinct seeds by appending `_u1` and `_u2` to the input `seed_str`, calls `proc_get_random_float` for each, and applies the transformation formula:

$$Z_0 = \sqrt{-2.0 \cdot \ln(U_1)} \cdot \cos(2\pi \cdot U_2)$$

The standard normal deviation value $Z_0$ is scaled and shifted to conform to the specified metrics:
$$\text{Result} = (Z_0 \cdot \text{stddev}) + \text{mean}$$

---

### 2.3 `faker.proc_get_spherical_coordinates`
Generates geolocation coordinates uniformly distributed on the surface of a three-dimensional sphere.

#### Arguments
*   `IN seed_str TEXT`: The distinct composite position text token.
*   `INOUT latitude DOUBLE PRECISION`: The variable populated with the calculated latitude degree inside $[-90.0, 90.0]$.
*   `INOUT longitude DOUBLE PRECISION`: The variable populated with the calculated longitude degree inside $[-180.0, 180.0]$.

#### Mathematical Algorithm
Picking a latitude uniformly between -90 and +90 causes clustering at the poles due to the convergence of meridian lines on a flat projection map. To maintain an even geographic distribution over a 3D sphere, the latitude must follow an inverse sine probability density function (PDF).

The procedure maps two uniform values ($U_1, U_2$) generated from isolated seed strings using the following transformations:
*   **Longitude ($\lambda$):** Simple linear mapping across a circle:
    $$\lambda = (U_1 \cdot 360.0) - 180.0$$
*   **Latitude ($\phi$):** Derived by applying the arc sine of a scaled linear variable to prevent polar distortion:
    $$\phi = \arcsin(2.0 \cdot U_2 - 1.0) \cdot \left(\frac{180}{\pi}\right)$$

---

## 2.4 `faker.proc_generate_phone`
Assembles a localized phone string matching structural national phone layout masks.

#### Arguments
*   `IN seed_str TEXT`: The composite position text segment.
*   `IN locale_str CHAR(3)`: The target country ISO identifier (`ENG` or `DEU`).
*   `INOUT phone_result TEXT`: The variable populated with the completely formatted phone string.

#### Layout Mechanics
The procedure reads a uniform random float to pick from multiple configuration mask templates depending on the requested country:
*   `ENG`: Alternate formats like `(###) ###-####`, `###-###-####`, or `+1 ### ### ####`.
*   `DEU`: Alternate formats like `+49 #### ######`, `0#### #######`, or `+49 (0) ### #######`.

It iterates through the chosen string structure mask character-by-character. Whenever a `#` placeholder is encountered, it uses a positionally anchored sub-seed to generate a uniform float, converts it to a single digit integer (`0-9`), and overwrites the placeholder. Non-placeholder characters (such as spaces, hyphens, or parentheses) are preserved exactly.

---

## 2.5 `faker.proc_evaluate_mask`
An internal formatting utility that evaluates and updates generic alphanumeric patterns, used primarily for postal code masking routines.

#### Arguments
*   `IN seed_str TEXT`: The baseline tracking seed.
*   `IN mask TEXT`: The target layout template string containing `#` tags.
*   `INOUT mask_result TEXT`: The variable populated with the resolved alphanumeric text output.

---

## 2.6 `faker.proc_generate_user_batch` (The Master Pipeline Engine)
The primary entry point used by the application layer. It runs a purely procedural execution loop to compile a structured batch of fake profiles and returns them through a database connection cursor.

#### Arguments
*   `IN p_base_seed INT`: The numeric baseline master seed provided by the end user via the web interface.
*   `IN p_locale CHAR(3)`: The target country specification code (`ENG` or `DEU`).
*   `IN p_batch_size INT`: The number of fake profiles to output (e.g., `10`).
*   `IN p_batch_offset INT`: The calculated data offset index (`batch_index * batch_size`) used to track pagination.
*   `INOUT p_result_cursor REFCURSOR`: The target portal cursor reference used to stream the dataset back to the FastAPI application layer.

#### Full Execution Flow Engine
1. **Lookup Verification:** Scans the metadata lookup structures (`lookup_first_names`, etc.) for the requested `p_locale` to capture the maximum `seq_id` tracking limits. If the tables are unpopulated for the requested locale, it raises an exception to protect the query context.
2. **Scratchpad Setup:** Instantiates an unindexed `TEMPORARY TABLE` named `temp_batch_output` within the current connection session to store the row records at maximum write speed.
3. **Procedural Loop:** Iterates from `0` to `p_batch_size - 1`. For each index iteration:
    *   Constructs a highly isolated row-level tracking string seed `v_row_seed`.
    *   Calls `proc_get_random_float` to determine demographic fields like gender split (50/50).
    *   Calculates indices for names, streets, and cities, and loads the matched database field strings into memory.
    *   Calls `proc_get_spherical_coordinates` to generate uniform global coordinate variables.
    *   Calls `proc_get_normal_float` to generate normally distributed physical attributes, such as height ($\mu=175$cm, $\sigma=10$) and weight ($\mu=75$kg, $\sigma=15$).
    *   Evaluates random attribute variation thresholds (e.g., a 15% chance to add prefixes like `Dr.` or `Mr.`/12% chance to add apartment tracking tags).
    *   Calls `proc_generate_phone` to build a localized phone string.
    *   Assembles a clean, normalized e-mail string by combining the selected first name, last name, a random two-digit number suffix, and a localized domain wrapper.
    *   Appends the compiled record straight into `temp_batch_output`.
4. **Cursor Delivery:** Opens the `p_result_cursor` to stream all records from the temporary table back to the application pool.

---

## 3. Transaction Execution Guide (Database CLI Testing)

Because stored procedures utilize a transactional `REFCURSOR` framework to deliver datasets, execution commands must be wrapped inside an explicit **SQL transaction block** (`BEGIN` ... `COMMIT`). This keeps the cursor handle open and readable by your testing client or application driver.

To test the entire procedural network manually inside any standard SQL terminal, run the following block:

```sql
-- 1. Open the transactional runtime scope
BEGIN;

-- 2. Execute the procedure, passing parameters and a named cursor token string
CALL faker.proc_generate_user_batch(
    42,          -- p_base_seed
    'ENG',       -- p_locale (ISO 639 CHAR(3))
    10,          -- p_batch_size
    0,           -- p_batch_offset
    'my_portal'  -- p_result_cursor
);

-- 3. Fetch the rows out of the active transactional cursor interface
FETCH ALL IN my_portal;

-- 4. Safely close out the tracking portal and clean up temporary tables
COMMIT;
```