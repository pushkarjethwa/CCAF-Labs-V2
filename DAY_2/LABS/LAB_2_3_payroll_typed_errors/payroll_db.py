"""Mock payroll back end (GIVEN - do not edit). In-memory copy of DATA/payroll.json plus
fault injection so every error class can be triggered deterministically.

Domain errors are raised as PayrollError subclasses. Turning them into tool results the
model can act on is YOUR job (lab.py, section 2)."""
import json
import pathlib

DATA = pathlib.Path(__file__).resolve().parent / "data"


class PayrollError(Exception):
    code = "UNEXPECTED_ERROR"

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details


class EmployeeNotFound(PayrollError):
    code = "EMPLOYEE_NOT_FOUND"


class PeriodClosed(PayrollError):
    code = "PAY_PERIOD_CLOSED"


class ApprovalRequired(PayrollError):
    code = "HR_APPROVAL_REQUIRED"


class DbLocked(PayrollError):
    code = "PAYROLL_DB_LOCKED"


class SimClock:
    """Simulated clock: sleep() records the delay and advances time, it never blocks."""

    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(float(seconds))
        self.now += float(seconds)


class PayrollDB:
    def __init__(self, clock: SimClock, data_path: pathlib.Path | None = None):
        d = json.loads((data_path or DATA / "payroll.json").read_text(encoding="utf-8"))
        self.threshold = d["approval_threshold_cents"]
        self.periods = dict(d["periods"])
        self.employees = dict(d["employees"])
        self.clock = clock
        self.adjustments: dict[str, dict] = {}   # idempotency_key -> row
        self.calls: list[tuple[str, str]] = []   # (operation, subject): every call that reached the DB
        self.lock_remaining = 0                  # N = next N apply calls are locked; -1 = locked forever

    def arm_lock(self, n: int) -> None:
        self.lock_remaining = n

    # ---- read operations -------------------------------------------------
    def lookup_employee(self, employee_id: str) -> dict:
        self.calls.append(("lookup_employee", employee_id))
        emp = self.employees.get(employee_id)
        if emp is None:
            raise EmployeeNotFound(f"No employee with id {employee_id}", employee_id=employee_id)
        return {"employee_id": employee_id, **emp}

    def _next_open(self, period: str) -> str | None:
        later = sorted(p for p, s in self.periods.items() if s == "open" and p > period)
        return later[0] if later else None

    def check_pay_period(self, period: str) -> dict:
        self.calls.append(("check_pay_period", period))
        status = self.periods.get(period)
        if status is None:
            raise EmployeeNotFound(f"Unknown pay period {period}", period=period)  # input-class problem
        nxt = period if status == "open" else self._next_open(period)
        return {"period": period, "status": status, "next_open_period": nxt}

    # ---- write operation -------------------------------------------------
    def apply_adjustment(self, employee_id: str, period: str, amount_cents: int, reason: str,
                         idempotency_key: str) -> dict:
        self.calls.append(("apply_adjustment", employee_id))
        if self.lock_remaining != 0:
            if self.lock_remaining > 0:
                self.lock_remaining -= 1
            raise DbLocked("Payroll database is locked by the nightly batch", resource="payroll_ledger")
        if idempotency_key in self.adjustments:                      # a retry must never double-pay
            return {**self.adjustments[idempotency_key], "duplicate": True}
        if employee_id not in self.employees:
            raise EmployeeNotFound(f"No employee with id {employee_id}", employee_id=employee_id)
        if self.periods.get(period) != "open":
            raise PeriodClosed(f"Pay period {period} is closed", period=period,
                               next_open_period=self._next_open(period))
        if abs(amount_cents) > self.threshold:
            raise ApprovalRequired("Adjustment exceeds the single-adjustment approval threshold",
                                   amount_cents=amount_cents, threshold_cents=self.threshold,
                                   required_role="HR_MANAGER", employee_id=employee_id, period=period,
                                   reason=reason)
        row = {"adjustment_id": f"PA-{len(self.adjustments) + 1:04d}", "employee_id": employee_id,
               "period": period, "amount_cents": amount_cents, "reason": reason,
               "idempotency_key": idempotency_key}
        self.adjustments[idempotency_key] = row
        return dict(row)
