from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from db.database import get_db
from db.models import PriceAlert, Product

router = APIRouter()


class AlertCreate(BaseModel):
    product_id:   int
    target_price: float
    email:        str   # use EmailStr if you add email-validator package


@router.post("/alerts")
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    """Set a price drop alert for a product."""
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    alert = PriceAlert(
        product_id   = payload.product_id,
        target_price = payload.target_price,
        email        = payload.email,
        is_active    = True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "message":    "Alert created successfully",
        "alert_id":   alert.id,
        "product":    product.name,
        "target":     payload.target_price,
        "email":      payload.email,
    }


@router.get("/alerts")
def list_alerts(email: str, db: Session = Depends(get_db)):
    """Get all active alerts for a given email."""
    alerts = (
        db.query(PriceAlert)
        .filter(PriceAlert.email == email, PriceAlert.is_active == True)
        .all()
    )
    return [
        {
            "alert_id":     a.id,
            "product_id":   a.product_id,
            "target_price": a.target_price,
            "created_at":   a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Cancel an alert."""
    alert = db.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False
    db.commit()
    return {"message": "Alert cancelled"}
