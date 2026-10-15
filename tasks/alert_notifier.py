from tasks.celery_app import celery_app
from db.database import SessionLocal
from db.models import PriceAlert, PriceRecord
from datetime import datetime, timezone

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import settings


def send_alert_email(
    to_email: str,
    product_name: str,
    target_price: float,
    current_price: float,
    product_url: str,
):
    """
    Send a price-drop alert email through Gmail SMTP.
    """

    subject = f"🔔 Price Drop Alert: {product_name[:50]}"

    body = f"""Hi there,

Great news! The price for the product you're tracking
has reached your target price.

Product  : {product_name}
Target   : ₹{target_price:,.2f}
Current  : ₹{current_price:,.2f}

Buy now before the price goes back up!

Product link:
{product_url}

— Price Comparison Engine
"""

    if not settings.smtp_user:
        raise RuntimeError(
            "SMTP_USER is not configured in .env"
        )

    if not settings.smtp_password:
        raise RuntimeError(
            "SMTP_PASSWORD is not configured in .env"
        )

    sender_email = (
        settings.alert_from_email
        or settings.smtp_user
    )

    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = to_email

    message.attach(
        MIMEText(
            body,
            "plain",
            "utf-8",
        )
    )

    try:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
        ) as server:

            server.login(
                settings.smtp_user,
                settings.smtp_password,
            )

            server.sendmail(
                sender_email,
                to_email,
                message.as_string(),
            )

        print(
            f"[AlertNotifier] ✅ Email sent successfully "
            f"to {to_email}"
        )

        return True

    except Exception as error:

        print(
            f"[AlertNotifier] ❌ Email failed: {error}"
        )

        return False


@celery_app.task(
    name="tasks.alert_notifier.check_and_notify"
)
def check_and_notify():
    """
    Check all active price alerts.

    If current price <= target price:
      1. Send email.
      2. Mark alert as inactive only after successful email.
      3. Store triggered_at timestamp.
    """

    db = SessionLocal()

    try:

        active_alerts = (
            db.query(PriceAlert)
            .filter(
                PriceAlert.is_active == True
            )
            .all()
        )

        print(
            f"[AlertNotifier] Checking "
            f"{len(active_alerts)} active alerts"
        )

        for alert in active_alerts:

            latest_record = (
                db.query(PriceRecord)
                .filter(
                    PriceRecord.product_id
                    == alert.product_id
                )
                .order_by(
                    PriceRecord.scraped_at.desc()
                )
                .first()
            )

            if not latest_record:

                print(
                    f"[AlertNotifier] ⚠️ No price history "
                    f"for alert {alert.id}"
                )

                continue

            current_price = float(
                latest_record.price
            )

            print(
                f"[AlertNotifier] Alert {alert.id} | "
                f"Current ₹{current_price:,.2f} | "
                f"Target ₹{alert.target_price:,.2f}"
            )

            if current_price <= float(
                alert.target_price
            ):

                product = alert.product

                email_sent = send_alert_email(
                    to_email=alert.email,
                    product_name=product.name,
                    target_price=float(
                        alert.target_price
                    ),
                    current_price=current_price,
                    product_url=product.url,
                )

                if email_sent:

                    alert.is_active = False

                    alert.triggered_at = (
                        datetime.now(timezone.utc)
                    )

                    print(
                        f"[AlertNotifier] ✅ Alert "
                        f"{alert.id} fired for "
                        f"{product.name[:40]} → "
                        f"{alert.email}"
                    )

                else:

                    print(
                        f"[AlertNotifier] ⚠️ Alert "
                        f"{alert.id} remains active "
                        f"because email delivery failed"
                    )

            else:

                print(
                    f"[AlertNotifier] No trigger for "
                    f"alert {alert.id}"
                )

        db.commit()

    except Exception as error:

        db.rollback()

        print(
            f"[AlertNotifier] ❌ Checker failed: "
            f"{error}"
        )

        raise

    finally:
        db.close()