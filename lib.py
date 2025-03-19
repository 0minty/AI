import asyncio, os, logging, aiosqlite
from mistralai import Mistral
from config import token_ai, token_tg, ID_ADM
from typing import Optional, Union
from aiogram import Dispatcher, Bot, F, filters
from aiogram import types, Router
from aiogram.filters.command import CommandStart, Command
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from main import *
