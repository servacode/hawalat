# حوالات — أوامر مختصرة للتطوير

.PHONY: up down backend frontend test lint

## تشغيل كل شيء عبر Docker (قاعدة + Redis + باكند + عامل + واجهة)
up:
	docker compose up --build

down:
	docker compose down

## تشغيل الباكند محلياً بلا Docker (يستخدم sqlite تلقائياً)
backend:
	cd backend && .venv/bin/python manage.py migrate && .venv/bin/python manage.py runserver

## تشغيل الواجهة محلياً
frontend:
	cd frontend && npm run dev

## الاختبارات والفحوص
test:
	cd backend && .venv/bin/python manage.py test

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint
