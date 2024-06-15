from django.db import models

class master_table(models.Model):

    id=models.IntegerField(primary_key=True)
    receipt_no=models.IntegerField()
    mode_of_pay=models.CharField(max_length=100)
    transaction_details=models.CharField(max_length=100)
    bank_name=models.CharField(max_length=100)
    amount=models.IntegerField()
    recieved_date=models.DateField()
    advance_amount=models.IntegerField()
    milestone_amount=models.IntegerField()
    status=models.CharField(max_length=100)
    created_on=models.DateField()
    bank_details_id=models.IntegerField()
    booking_id=models.IntegerField()
    created_by_id=models.IntegerField()
    customer_receipt_tpye=models.CharField(max_length=100)
    updated_on=models.TimeField()



    class Meta:
        managed = False  # No migrations will be created for this model
        db_table = 'master_table'

class payment_schedule_tablename(models.Model):
    id=models.IntegerField(primary_key=True)
    percent = models.IntegerField()
    GSTper=models.IntegerField()
    invoice_no=models.IntegerField()
    invoice_on=models.DateField()
    due_date=models.DateField()
    amount=models.IntegerField()
    gst=models.CharField(max_length=100)
    total_amount=models.IntegerField()
    total_paid_amount=models.IntegerField()
    total_balance_amount=models.IntegerField()
    Stage=models.CharField(max_length=100)
    Stage_name = models.IntegerField()
    booking_id=models.IntegerField()
    payment_schedule_id=models.IntegerField()

    class Meta:
        managed = False  # No migrations will be created for this model
        db_table = 'payment_schedule_tablename'

class reference_master_table(models.Model):
    id=models.IntegerField(primary_key=True)
    against=models.CharField(max_length=100)
    amount=models.IntegerField()
    object_id=models.IntegerField()
    content_type_id=models.IntegerField()
    receipt_id=models.IntegerField()

class Meta:
    managed = False  # No migrations will be created for this model
    db_table = 'reference_master_table'

'''
models.CharField(max_length=100)
models.IntegerField()
models.FloatField()
models.DateField()
models.TimeField()



'''

# models.py


class InterestReport(models.Model):
    stage_name = models.CharField(max_length=100)
    due_date = models.DateField()
    initial_amount = models.DecimalField(max_digits=10, decimal_places=2)
    received_date = models.DateField()
    customer_receipt_type = models.CharField(max_length=100)
    received_amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_id = models.IntegerField()
    date_difference = models.IntegerField()
    interest_per = models.DecimalField(max_digits=10, decimal_places=2)
    interest_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_interest_18_percent = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_interest_gst = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['stage_name', 'due_date', 'received_date']
