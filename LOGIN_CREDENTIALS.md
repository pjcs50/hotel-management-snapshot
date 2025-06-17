# 🔐 Hotel Management System - Login Credentials

## Permanent Test Accounts

These accounts are **PERMANENTLY** configured in the system and will be recreated automatically if removed. They are essential for testing and system access.

### 🏨 Test Credentials (Use: `password`)

| Email | Password | Role | Access Level |
|-------|----------|------|-------------|
| `admin@example.com` | `password` | **Admin** | Full system access, user management, reports |
| `manager@example.com` | `password` | **Manager** | Operations management, reports, staff oversight |
| `housekeeping@example.com` | `password` | **Housekeeping** | Room status updates, cleaning schedules |
| `reception@example.com` | `password` | **Receptionist** | Guest check-in/out, booking management |
| `customer@example.com` | `password` | **Customer** | Guest booking, profile management |

---

## 🛡️ System Protection

### Automatic Recreation
- These accounts are **automatically created** on app startup
- If deleted, they will be **restored** on next system restart
- Password is always reset to `password` for consistency

### Manual Recreation
If you need to manually recreate these accounts, run:
```bash
python3 ensure_test_accounts.py
```

### Verification
To verify accounts exist:
```bash
python3 -c "from app_factory import create_app; from app.models import User; app = create_app(); app.app_context().push(); print('Test accounts:'); [print(f'{u.email} - {u.role}') for u in User.query.filter(User.email.like('%@example.com')).all()]"
```

---

## 🚀 Quick Start Login

1. **Admin Dashboard**: Use `admin@example.com` / `password`
2. **Manager Dashboard**: Use `manager@example.com` / `password`
3. **Receptionist Desk**: Use `reception@example.com` / `password`
4. **Housekeeping**: Use `housekeeping@example.com` / `password`
5. **Customer Portal**: Use `customer@example.com` / `password`

---

## ⚠️ Important Notes

- **DO NOT** rely on these accounts for production
- These are **TEST ACCOUNTS ONLY**
- The simple password bypasses normal security validation
- Accounts are recreated with basic security for testing convenience
- For production, create proper accounts with strong passwords

---

## 🔧 Technical Implementation

- Accounts created in: `app/utils/test_accounts.py`
- Auto-creation trigger: `app_factory.py` (on startup)
- Manual creation script: `ensure_test_accounts.py`
- Password hashing: Direct Werkzeug hash (bypasses validation)

**These credentials are PERMANENT and PROTECTED against accidental removal.** 