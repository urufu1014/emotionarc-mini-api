from flask import Flask, request, jsonify
from google.cloud import firestore
from datetime import datetime, timedelta, timezone
import logging, sys, traceback, json

app = Flask(__name__)
db  = firestore.Client()

# ――― 設定 ―――
LIMIT     = 150          # 1 ユーザー当たり残数
RESET_HR  = 24           # 何時間でリセットするか

# ---------- ヘルスチェック ----------
@app.route("/ping")
def ping():
    return jsonify(status="ok"), 200


# ---------- 残数カウント ----------
@app.route("/rate-limit", methods=["GET"])
def rate_limit():
    try:
        uid      = request.args.get("uid", "testuser")
        doc_ref  = db.collection("usage").document(uid)

        @firestore.transactional
        def update(txn):
            snap = doc_ref.get(transaction=txn).to_dict() or {
                "remaining": LIMIT,
                "reset"    : datetime.now(timezone.utc)
            }

            # リセット判定
            if datetime.now(timezone.utc) > snap["reset"] + timedelta(hours=RESET_HR):
                snap["remaining"] = LIMIT
                snap["reset"]     = datetime.now(timezone.utc)

            if snap["remaining"] <= 0:
                return jsonify(status="limit_exceeded", remaining=0), 429

            snap["remaining"] -= 1
            txn.set(doc_ref, snap)
            return jsonify(status="ok", remaining=snap["remaining"]), 200

        txn = db.transaction()
        return update(txn)

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return jsonify(status="error", detail=str(e)), 500


# ---------- スクリプト登録 ----------
@app.route("/pool-put", methods=["POST"])
def pool_put():
    try:
        uid   = request.args.get("uid", "testuser")
        body  = request.get_json(force=True) or {}
        db.collection("script_pool").document(uid).set({
            "script"  : json.dumps(body, ensure_ascii=False),
            "updated" : datetime.now(timezone.utc)
        })
        return jsonify(status="accepted"), 202
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return jsonify(status="error", detail=str(e)), 500


# ---------- スクリプト取得 ----------
@app.route("/pool-get", methods=["GET"])
def pool_get():
    try:
        uid = request.args.get("uid", "testuser")
        doc = db.collection("script_pool").document(uid).get()
        if not doc.exists:
            return jsonify(status="ready"), 200
        data = doc.to_dict()
        return jsonify(status="ready", script=data["script"]), 200
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return jsonify(status="error", detail=str(e)), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
