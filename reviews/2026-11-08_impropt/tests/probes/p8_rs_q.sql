connect 'probe8' user SYSDBA;
set explain on;
set planonly on;
-- S1: ordered; leader ra navigates ra_x, rb hashed (4.2M > 4M capacity) -> restart path
select ra.x, rb.id from ra join rb on rb.g = ra.g where ra.x < 600001 order by ra.x;
-- S2: same without ORDER BY (control)
select ra.x, rb.id from ra join rb on rb.g = ra.g where ra.x < 600001;
-- S3: ordered with a local filter on rb too
select ra.x, rb.id from ra join rb on rb.g = ra.g where ra.x < 600001 and rb.id > 0 order by ra.x;
