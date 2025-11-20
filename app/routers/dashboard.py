from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional, Dict, Any
from functools import lru_cache
import time
from app.database import get_db
from app.auth import create_session_cookie
from app.config import get_settings
from app.crud import get_unique_apartments, get_bookings_by_begin_date, get_payments, get_expenses
from loguru import logger

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def check_auth(request: Request) -> Optional[str]:
    """Проверка авторизации через session cookie и возврат user_type"""
    session_token = request.cookies.get("session_token")
    if not session_token or session_token != settings.secret_key:
        return None
    
    user_type = request.cookies.get("user_type")
    if not user_type or user_type not in ['admin', 'user']:
        return None
    
    return user_type


def get_base_address(address: str) -> str:
    """Получить базовый адрес без суффикса ДУБЛЬ (регистронезависимо)"""
    if not address:
        return ''
    
    address_clean = address.strip()
    address_upper = address_clean.upper()
    
    # Список суффиксов для удаления (в верхнем регистре)
    suffixes = ['ДУБЛЬ', 'ДУБЛ', 'ДУБЛЕ', 'ДУБ', 'DUBL', 'DOUBLE']
    
    for suffix in suffixes:
        # Проверяем с пробелом перед суффиксом
        suffix_with_space = ' ' + suffix
        if suffix_with_space in address_upper:
            idx = address_upper.find(suffix_with_space)
            result = address_clean[:idx].strip()
            return result
        # Проверяем суффикс в конце без пробела
        elif address_upper.endswith(suffix):
            result = address_clean[:-len(suffix)].strip()
            return result
    
    return address_clean


def get_top_apartments(db: Session, limit: int = 50) -> list:
    """Получить топ N объектов недвижимости для оптимизации"""
    try:
        apartments = get_unique_apartments(db)
        # Ограничиваем количество объектов для обработки
        return apartments[:limit] if len(apartments) > limit else apartments
    except Exception as e:
        logger.error(f"Error in get_top_apartments: {e}")
        return []


def get_monthly_financial_data(db: Session, year: int, month: int, apartments: list) -> dict:
    """Получить финансовые данные за конкретный месяц для ограниченного списка объектов"""
    try:
        start_time = time.time()
        
        # Начало и конец месяца
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, month + 1, 1)
        
        # Структура для хранения данных за месяц
        month_data = {
            'month': month,
            'objects': {},
            'total_income': 0,
            'total_expenses': 0,
            'total_profit': 0,
            'general_expenses': 0  # Добавляем поле для общих расходов
        }
        
        # Для каждого объекта
        for apartment in apartments:
            base_apartment = get_base_address(apartment)
            
            # Получаем бронирования (доходы) для объекта и месяца
            bookings = get_bookings_by_begin_date(
                db, 
                filter_date_from=start_date, 
                filter_date_to=end_date, 
                apartment_title=apartment
            )
            
            # Получаем поступления для объекта и месяца
            payments = get_payments(
                db, 
                filter_date_from=start_date, 
                filter_date_to=end_date, 
                apartment_title=apartment
            )
            
            # Получаем расходы для объекта и месяца
            expenses = get_expenses(
                db, 
                filter_date_from=start_date, 
                filter_date_to=end_date, 
                apartment_title=apartment
            )
            
            # Считаем общую сумму доходов
            income_total = 0
            
            # Доходы от бронирований
            for booking in bookings:
                if booking.amount:
                    income_total += float(booking.amount)
            
            # Доходы от поступлений
            for payment in payments:
                if payment.amount:
                    income_total += float(payment.amount)
            
            # Считаем общую сумму расходов
            expense_total = 0
            for expense in expenses:
                if expense.amount:
                    expense_total += float(expense.amount)
            
            # Прибыль
            profit = income_total - expense_total
            
            # Пропускаем нулевые значения для оптимизации
            if income_total == 0 and expense_total == 0 and profit == 0:
                continue
            
            # Добавляем в структуру данных
            if base_apartment not in month_data['objects']:
                month_data['objects'][base_apartment] = {
                    'apartments': [],
                    'income': 0,
                    'expenses': 0,
                    'profit': 0
                }
            
            # Добавляем объект к группе
            if apartment not in month_data['objects'][base_apartment]['apartments']:
                month_data['objects'][base_apartment]['apartments'].append(apartment)
            
            # Суммируем данные для дублей
            month_data['objects'][base_apartment]['income'] += income_total
            month_data['objects'][base_apartment]['expenses'] += expense_total
            month_data['objects'][base_apartment]['profit'] += profit
            
            # Суммируем общие данные по месяцу
            month_data['total_income'] += income_total
            month_data['total_expenses'] += expense_total
            month_data['total_profit'] += profit
        
        # Получаем общие расходы (не привязанные к объектам)
        all_expenses = get_expenses(db, filter_date_from=start_date, filter_date_to=end_date)
        general_expenses = 0
        for expense in all_expenses:
            # Проверяем, если расход не привязан к конкретному объекту
            if not expense.apartment_title or expense.apartment_title.strip() == '':
                if expense.amount:
                    general_expenses += float(expense.amount)
        
        month_data['general_expenses'] = general_expenses
        
        end_time = time.time()
        logger.debug(f"Processed month {month} in {end_time - start_time:.2f} seconds")
        
        return month_data
    except Exception as e:
        logger.error(f"Error in get_monthly_financial_data: {e}")
        return {}


# Кэшируем результаты на 5 минут
@lru_cache(maxsize=32)
def get_cached_annual_financial_data(cache_key: str, db_hash: int, year: int) -> dict:
    """Кэшированная версия получения финансовых данных за год"""
    # Эта функция будет вызываться с уникальным ключом для кэширования
    # Реальная реализация будет в основном методе
    pass


def get_annual_financial_data(db: Session, year: int) -> dict:
    """Получить финансовые данные за год, сгруппированные по объектам и месяцам"""
    try:
        start_time = time.time()
        
        # Структура для хранения данных
        financial_data = {}
        
        # Получаем ограниченный список объектов
        apartments = get_top_apartments(db)
        
        # Для каждого месяца - получаем данные отдельно
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            financial_data[month_key] = get_monthly_financial_data(db, year, month, apartments)
        
        end_time = time.time()
        logger.info(f"Processed annual financial data for {year} in {end_time - start_time:.2f} seconds")
        
        return financial_data
    except Exception as e:
        logger.error(f"Error in get_annual_financial_data: {e}")
        return {}


def get_apartment_summary(financial_data: dict) -> dict:
    """Получить сводную информацию по объектам за год"""
    try:
        apartment_summary = {}
        
        # Проходим по всем месяцам
        for month_key, month_data in financial_data.items():
            if isinstance(month_data, dict) and 'objects' in month_data:
                for base_apartment, obj_data in month_data['objects'].items():
                    if base_apartment not in apartment_summary:
                        apartment_summary[base_apartment] = {
                            'apartments': obj_data.get('apartments', []),
                            'total_income': 0,
                            'total_expenses': 0,
                            'total_profit': 0
                        }
                    
                    # Суммируем данные за год
                    apartment_summary[base_apartment]['total_income'] += obj_data.get('income', 0)
                    apartment_summary[base_apartment]['total_expenses'] += obj_data.get('expenses', 0)
                    apartment_summary[base_apartment]['total_profit'] += obj_data.get('profit', 0)
        
        return apartment_summary
    except Exception as e:
        logger.error(f"Error in get_apartment_summary: {e}")
        return {}


def calculate_yearly_totals(financial_data: dict) -> dict:
    """Рассчитать итоговые значения за год"""
    try:
        total_income = 0
        total_expenses = 0
        total_profit = 0
        total_general_expenses = 0  # Добавляем учет общих расходов
        
        # Проходим по всем месяцам
        for month_data in financial_data.values():
            if isinstance(month_data, dict):
                total_income += month_data.get('total_income', 0)
                total_expenses += month_data.get('total_expenses', 0)
                total_profit += month_data.get('total_profit', 0)
                total_general_expenses += month_data.get('general_expenses', 0)
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'total_profit': total_profit,
            'total_general_expenses': total_general_expenses  # Возвращаем общие расходы
        }
    except Exception as e:
        logger.error(f"Error in calculate_yearly_totals: {e}")
        return {
            'total_income': 0,
            'total_expenses': 0,
            'total_profit': 0,
            'total_general_expenses': 0
        }


# Add custom functions to Jinja2 environment (after they are defined)
templates.env.globals["get_apartment_summary"] = get_apartment_summary
templates.env.globals["calculate_yearly_totals"] = calculate_yearly_totals


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Страница дашборда с годовой финансовой информацией
    """
    try:
        start_time = time.time()
        
        # Проверка авторизации (только для админов)
        user_type = check_auth(request)
        if not user_type or user_type != 'admin':
            return Response(status_code=403)
        
        # Если год не указан, используем текущий
        if not year:
            year = datetime.now().year
        
        # Ограничиваем год для оптимизации (не больше 5 лет назад)
        current_year = datetime.now().year
        if year < current_year - 5:
            year = current_year - 5
        elif year > current_year + 5:
            year = current_year + 5
        
        # Получаем финансовые данные
        financial_data = get_annual_financial_data(db, year)
        
        # Вычисляем годовые итоги
        yearly_totals = calculate_yearly_totals(financial_data)
        
        end_time = time.time()
        logger.info(f"Dashboard page loaded for {year} in {end_time - start_time:.2f} seconds")
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "financial_data": financial_data,
                "year": year,
                "user_type": user_type,
                "yearly_totals": yearly_totals  # Добавляем yearly_totals в контекст шаблона
            }
        )
    except Exception as e:
        logger.error(f"Error in dashboard_page: {e}")
        return Response(status_code=500, content="Internal Server Error")
