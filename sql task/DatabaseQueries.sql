-- SQL to retrieve:
-- employee's position, department info
SELECT 
Employee.first_name,
Employee.last_name,
Employee.number,
Employee.email,
Employee.hire_date,
Employee.base_salary,
Department.dept_name,
Position.position_name

FROM Employee 
JOIN Department ON Department.department_id = Employee.department_id
JOIN Position ON Position.position_id = Employee.position_id
ORDER BY Employee.first_name


--attendance summaries
SELECT
a.attendance_date,
a.status,
a.check_in,
a.check_out,
a.hours_worked,
a.overtime_hours,
a.missing_hours,
e.first_name,
e.last_name,
e.email,
e.number,
e.hire_date,
d.dept_name,
p.position_name
FROM Attendance a
JOIN Employee e ON a.employee_id = e.employee_id
JOIN Department d ON e.department_id = d.department_id
JOIN Position p ON e.position_id = p.position_id
ORDER BY e.hire_date


--Payroll calculations
SELECT
e.first_name,
e.last_name,
e.base_salary,
e.number,
e.email,
d.dept_name,
p.position_name,
pr.payroll_month,
COALESCE(pr.allowance,0) AS allowance,
COALESCE(pr.deduction,0) AS deduction,
(e.base_salary + COALESCE(pr.allowance,0)) AS calc_gross_salary,
((e.base_salary + COALESCE(pr.allowance,0)) - COALESCE(pr.deduction,0)) AS calc_net_salary
FROM Payroll pr
JOIN Employee e ON e.employee_id = pr.employee_id
JOIN Department d ON d.department_id = e.department_id
JOIN Position p ON p.position_id = e.position_id
ORDER BY pr.payroll_month

--Employee leave balance report for each leave type and balance period.
SELECT
    e.employee_id,
    e.first_name,
    e.last_name,
    d.dept_name,
    p.position_name,
    lt.leave_type,
    lb.allocation_date,
    lb.expiration_date,
    SUM(lb.allocated_days) AS allocated_days,
    SUM(lb.used_days)      AS used_days,
    SUM(lb.balance)        AS remaining_balance
FROM leavebalance lb
JOIN employee e   ON e.employee_id = lb.employee_id
JOIN department d ON d.department_id = e.department_id
JOIN position p   ON p.position_id   = e.position_id
JOIN leavetype lt ON lt.leave_id     = lb.leave_id
WHERE lb.expiration_date >= CURRENT_DATE
GROUP BY
    e.employee_id, e.first_name, e.last_name,
    d.dept_name, p.position_name,
    lt.leave_type, lb.allocation_date, lb.expiration_date
HAVING SUM(lb.balance) > 0
ORDER BY remaining_balance DESC, e.employee_id;

--Employee leave requests report  
SELECT
    lr.leaverequest_id,
    lr.requested_date,
    lr.start_date,
    lr.end_date,
    lr.requested_days,
    ((lr.end_date - lr.start_date) + 1) AS calc_days_check,
    lr.status,
    lt.leave_type,
    lt.is_paid,
    e.employee_id,
    e.first_name,
    e.last_name,
    e.number,
    e.email,
    e.hire_date,
    d.dept_name,
    p.position_name
FROM leaverequest lr
JOIN employee e   ON e.employee_id = lr.employee_id
JOIN department d ON d.department_id = e.department_id
JOIN position p   ON p.position_id   = e.position_id
JOIN leavetype lt ON lt.leave_id     = lr.leave_id
ORDER BY lr.requested_date DESC, d.dept_name, e.employee_id;