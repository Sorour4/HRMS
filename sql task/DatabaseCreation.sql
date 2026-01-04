CREATE TABLE IF NOT EXISTS Position(
    position_id SERIAL PRIMARY KEY,
    position_name VARCHAR(200) NOT NULL,
    head_count INT NOT NULL,
    department_id INT
);

CREATE TABLE IF NOT EXISTS Employee (
    employee_id SERIAL PRIMARY KEY,
    first_name VARCHAR(200),
    last_name VARCHAR(200),
    number INT UNIQUE,
    email VARCHAR(200) UNIQUE,
    hire_date DATE NOT NULL,
    base_salary INT NOT NULL,
    position_id INT REFERENCES Position(position_id),
    manager_id INT REFERENCES Employee(employee_id) ON DELETE SET NULL,
    department_id INT
);

CREATE TABLE IF NOT EXISTS Department(
    department_id SERIAL PRIMARY KEY,
    dept_name VARCHAR(200),
    dept_location VARCHAR(200),
    manager_id INT REFERENCES Employee(employee_id),
);

ALTER TABLE Position
ADD CONSTRAINT fk_position_department
FOREIGN KEY (department_id) REFERENCES Department(department_id);

ALTER TABLE Employee
ADD CONSTRAINT fk_employee_department
FOREIGN KEY (department_id) REFERENCES Department(department_id);

CREATE TABLE IF NOT EXISTS LeaveType (
    leave_id SERIAL PRIMARY KEY,
    leave_type VARCHAR(200) NOT NULL,
    leave_description VARCHAR(200),
    max_days INT,
    is_paid BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS LeaveBalance (
    leavebalance_id SERIAL PRIMARY KEY,
    employee_id INT REFERENCES Employee(employee_id),
    leave_id INT REFERENCES LeaveType(leave_id),
    allocated_days INT,
    used_days INT,
    balance INT GENERATED ALWAYS AS (allocated_days - used_days) STORED,
    allocation_date DATE,
    expiration_date DATE,
    CONSTRAINT
    UNIQUE (employee_id, leave_id, allocation_date)
);

CREATE TABLE IF NOT EXISTS Payroll (
    payroll_id SERIAL PRIMARY KEY,
    employee_id INT REFERENCES Employee(employee_id),
    payroll_month INT CHECK (payroll_month BETWEEN 1 AND 12),
    payroll_year INT CHECK (payroll_year >= 2010),
    allowance INT,
    deduction INT,
    gross_salary INT,
    net_salary INT
);

CREATE TYPE ATTENDANCESTATUS AS ENUM (
    'PRESENT',
    'ABSENT',
    'LEAVE'
);

CREATE TABLE IF NOT EXISTS Attendance (
    attendance_id SERIAL PRIMARY KEY,
    employee_id INT REFERENCES Employee(employee_id),
    attendance_date DATE,
    status ATTENDANCESTATUS NOT NULL DEFAULT 'ABSENT',
    check_in TIMESTAMP,
    check_out TIMESTAMP,

    hours_worked NUMERIC(6,2)
    GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (check_out - check_in)) / 3600
    ) STORED,

    overtime_hours NUMERIC(6,2)
    GENERATED ALWAYS AS (
        GREATEST(
            EXTRACT(EPOCH FROM (check_out - check_in)) / 3600 - 8,
            0
        )
    ) STORED,

    missing_hours NUMERIC(6,2)
    GENERATED ALWAYS AS (
        GREATEST(
            8 - EXTRACT(EPOCH FROM (check_out - check_in)) / 3600,
            0
        )
    ) STORED,
    CONSTRAINT chk_checkout_after_checkin
    CHECK (check_out IS NULL OR check_out > check_in),
    CONSTRAINT
    UNIQUE (employee_id, attendance_date)
);

CREATE TYPE LEAVESTATUS AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'CANCELLED'
);

CREATE TABLE IF NOT EXISTS LeaveRequest (
    leaverequest_id SERIAL PRIMARY KEY,
    employee_id INT REFERENCES Employee(employee_id),
    leave_id INT REFERENCES LeaveType(leave_id),
    start_date DATE,
    end_date DATE,
    requested_days INT,
    requested_date DATE,
    status LEAVESTATUS NOT NULL DEFAULT 'PENDING'
);

