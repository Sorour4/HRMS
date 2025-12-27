-- TODO: Always try to avoid SELECT *, this affects the performance a lot
-- it's better to specify the exact fields you want to return for better performance.
--page number pagination is relient on logic that offset = (pagenumber-1)*pagesize
SELECT *
FROM employee
ORDER BY id
LIMIT 10 OFFSET 20;  --pagesize = 10


--normal query to select the first 25 records
SELECT *
FROM employee
ORDER BY id
LIMIT 25;