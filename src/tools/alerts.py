import logging
import uuid
from typing import Optional
from datetime import datetime
from src.mcp_server import mcp
from src.database.connection import get_db
from src.security.auth import get_authenticated_context
from src.market.api import get_live_price, resolve_ticker

logger = logging.getLogger("investmind.tools.alerts")

@mcp.tool()
async def create_alert(symbol: str, alert_type: str, condition: str, target_value: str) -> dict:
    """
    Creates an alert setting.
    Alert types: PRICE, VOLUME, DIVIDEND, NEWS, RESULTS, CORP_ACTION, TARGET_PRICE, STOP_LOSS, RSI, MACD.
    Condition: ABOVE, BELOW, TRIGGER.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        symbol = symbol.upper().strip()
        alert_type = alert_type.upper().strip()
        condition = condition.upper().strip()
        target_value = target_value.strip()
        
        # Verify valid inputs
        valid_types = ["PRICE", "VOLUME", "DIVIDEND", "NEWS", "RESULTS", "CORP_ACTION", "TARGET_PRICE", "STOP_LOSS", "RSI", "MACD"]
        if alert_type not in valid_types:
            return {"success": False, "message": f"Unsupported alert type: {alert_type}. Supported: {valid_types}"}
            
        alert_id = str(uuid.uuid4())[:8]
        alert = {
            "user_id": uid,
            "alert_id": alert_id,
            "symbol": symbol,
            "alert_type": alert_type,
            "condition": condition,
            "target_value": target_value,
            "status": "ACTIVE",
            "created_at": datetime.utcnow(),
            "triggered_at": None
        }
        await db["alerts"].insert_one(alert)
        return {"success": True, "alert_id": alert_id, "message": f"Alert {alert_id} created successfully for {symbol}."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def list_alerts() -> list[dict]:
    """
    Lists all of the user's active, paused, and triggered alerts.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return []
            
        cursor = db["alerts"].find({"user_id": uid})
        alerts = []
        async for doc in cursor:
            alerts.append({
                "alert_id": doc["alert_id"],
                "symbol": doc["symbol"],
                "alert_type": doc["alert_type"],
                "condition": doc["condition"],
                "target_value": doc["target_value"],
                "status": doc["status"],
                "created_at": doc["created_at"].strftime("%Y-%m-%d %H:%M:%S") if doc.get("created_at") else ""
            })
        return alerts
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        return []

@mcp.tool()
async def update_alert(alert_id: str, condition: Optional[str] = None, target_value: Optional[str] = None) -> dict:
    """
    Updates an alert's target values or triggers.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        updates = {}
        if condition:
            updates["condition"] = condition.upper().strip()
        if target_value:
            updates["target_value"] = target_value.strip()
            
        if not updates:
            return {"success": False, "message": "No updates provided."}
            
        result = await db["alerts"].update_one(
            {"user_id": uid, "alert_id": alert_id},
            {"$set": updates}
        )
        if result.matched_count > 0:
            return {"success": True, "message": f"Alert {alert_id} updated successfully."}
        return {"success": False, "message": f"Alert {alert_id} not found."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def delete_alert(alert_id: str) -> dict:
    """
    Deletes an alert setting.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        result = await db["alerts"].delete_one({"user_id": uid, "alert_id": alert_id})
        if result.deleted_count > 0:
            return {"success": True, "message": f"Alert {alert_id} deleted successfully."}
        return {"success": False, "message": f"Alert {alert_id} not found."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def pause_alert(alert_id: str) -> dict:
    """
    Pauses an alert evaluation.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        result = await db["alerts"].update_one(
            {"user_id": uid, "alert_id": alert_id},
            {"$set": {"status": "PAUSED"}}
        )
        if result.matched_count > 0:
            return {"success": True, "message": f"Alert {alert_id} paused."}
        return {"success": False, "message": f"Alert {alert_id} not found."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def resume_alert(alert_id: str) -> dict:
    """
    Resumes a paused alert.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return {"success": False, "message": "Database connection unavailable."}
            
        result = await db["alerts"].update_one(
            {"user_id": uid, "alert_id": alert_id},
            {"$set": {"status": "ACTIVE"}}
        )
        if result.matched_count > 0:
            return {"success": True, "message": f"Alert {alert_id} resumed."}
        return {"success": False, "message": f"Alert {alert_id} not found."}
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
async def get_triggered_alerts() -> list[dict]:
    """
    Evaluates active alerts against live prices and returns triggered notifications.
    """
    try:
        uid, _ = get_authenticated_context()
        db = await get_db()
        if db is None:
            return []
            
        cursor = db["alerts"].find({"user_id": uid, "status": "ACTIVE"})
        triggered = []
        
        async for doc in cursor:
            symbol = doc["symbol"]
            alert_type = doc["alert_type"]
            condition = doc["condition"]
            target = doc["target_value"]
            alert_id = doc["alert_id"]
            
            is_triggered = False
            current_value_str = ""
            
            # Simple Price Evaluation
            if alert_type in ["PRICE", "TARGET_PRICE", "STOP_LOSS"]:
                ticker = await resolve_ticker(symbol)
                price = await get_live_price(ticker)
                
                if price is not None:
                    current_value_str = f"Rs. {price}"
                    target_price = float(target)
                    if condition == "ABOVE" and price > target_price:
                        is_triggered = True
                    elif condition == "BELOW" and price < target_price:
                        is_triggered = True
                        
            if is_triggered:
                # Update status in db
                await db["alerts"].update_one(
                    {"alert_id": alert_id},
                    {"$set": {"status": "TRIGGERED", "triggered_at": datetime.utcnow()}}
                )
                triggered.append({
                    "alert_id": alert_id,
                    "symbol": symbol,
                    "alert_type": alert_type,
                    "condition": condition,
                    "target_value": target,
                    "triggered_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": f"Alert triggered for {symbol}: current value is {current_value_str} (Target: {condition} {target})."
                })
        return triggered
    except Exception as e:
        logger.error(f"Error checking triggered alerts: {e}")
        return []
