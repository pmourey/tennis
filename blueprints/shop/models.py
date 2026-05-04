# Source Generated with Decompyle++
# File: models.cpython-310.pyc (Python 3.10)

from extensions import db

class Racquet(db.Model):
    __tablename__ = 'racquet'
    id = db.Column(db.Integer, True, **('primary_key',))
    name = db.Column(db.String(100), False, **('nullable',))
    brand = db.Column(db.String(50), False, **('nullable',))
    head_size = db.Column(db.Float, True, **('nullable',))
    length = db.Column(db.Float, True, **('nullable',))
    strung_weight = db.Column(db.Float, True, **('nullable',))
    unstrung_weight = db.Column(db.Float, True, **('nullable',))
    balance = db.Column(db.Float, True, **('nullable',))
    swingweight = db.Column(db.Integer, True, **('nullable',))
    stiffness = db.Column(db.Integer, True, **('nullable',))
    beam_width = db.Column(db.String(20), True, **('nullable',))
    string_pattern = db.Column(db.String(10), True, **('nullable',))
    string_tension = db.Column(db.String(20), True, **('nullable',))
    price = db.Column(db.Float, True, **('nullable',))
    url = db.Column(db.String(500), True, **('nullable',))
    image_url = db.Column(db.String(500), True, **('nullable',))
    image_local = db.Column(db.String(200), True, **('nullable',))
    player_type = db.Column(db.String(50), True, **('nullable',))
    composition = db.Column(db.String(100), True, **('nullable',))
    color = db.Column(db.String(50), True, **('nullable',))
    is_current = db.Column(db.Boolean, False, False, '0', **('default', 'nullable', 'server_default'))
    created_at = db.Column(db.DateTime, db.func.now(), **('default',))
    
    def __repr__(self):
        return f'''{self.brand} {self.name}'''

    
    def balance_label(self):
        if self.balance is None:
            return 'N/A'
        if None.balance < 0:
            return f'''{abs(self.balance):.1f} pts HL'''
        if None.balance > 0:
            return f'''{self.balance:.1f} pts HH'''

    balance_label = property(balance_label)

