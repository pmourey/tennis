from datetime import datetime

birthDate = datetime(1967, 6 , 23)
today = datetime.now()
today = datetime(2024, 6 , 22)
age = today.year - birthDate.year - ((today.month, today.day) < (birthDate.month, birthDate.day))

print(age)