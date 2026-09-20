import pymysql as pm

class conn:
    def __init__(self):
        self.banco = pm.connect(
            user="root",
            host="localhost",
            password="Mpso_7890@",
            database="sgrub",
            port=3306
        )