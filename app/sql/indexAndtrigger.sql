
-- Index para agrupar y ordenar por fecha y estado
CREATE INDEX idx_transactions_date_status ON transactions (DATE(ts), status);

-- Alternativamente, solo por fecha
CREATE INDEX idx_transactions_date ON transactions (DATE(ts));


CREATE OR REPLACE FUNCTION validate_amount()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount < 0 OR NEW.amount > 2000 THEN
        RAISE EXCEPTION 'El valor de amount (%.2f) debe estar entre 0 y 2000', NEW.amount;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;



CREATE TRIGGER trigger_validate_amount
BEFORE INSERT OR UPDATE ON transactions
FOR EACH ROW
EXECUTE FUNCTION validate_amount();
