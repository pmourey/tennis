In Flask with SQLAlchemy, you can add new ORM models without recreating all existing ones by using **database migrations** with Alembic, which is integrated into Flask-Migrate. Here's the step-by-step process:

### **1. Ensure Flask-Migrate is Installed**
If you haven’t installed it yet, install Flask-Migrate:

```bash
pip install Flask-Migrate
```

### **2. Initialize Flask-Migrate (If Not Already Done)**
If your project doesn’t have a migration setup yet, initialize it:

```bash
# In your tennis directory
export FLASK_APP=app.py
flask db init
```

### **3. Create a New SQLAlchemy Model**
Add your new model to your SQLAlchemy models file (e.g., `models.py`):

```python
from app import db

class NewModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
```

### **4. Generate a Migration Script**
Run the following command to detect the new model and create a migration:

```bash
flask db migrate -m "Added NewModel"
```

This will create a new migration script inside the `migrations/versions/` directory.

### **5. Apply the Migration**
Run:

```bash
flask db upgrade
```

This will apply the new model to your database without affecting the existing models.

### **6. Verify the Database**
Check your database to confirm that the new table has been added.

---

#### **Key Notes:**
- Never run `db.create_all()` in production—it skips migrations and can lead to inconsistencies.
- Always use `flask db migrate` and `flask db upgrade` to track database schema changes.
- If you make changes to existing models, make sure to generate and apply new migrations accordingly.

Would you like help debugging any issues with migrations? 🚀