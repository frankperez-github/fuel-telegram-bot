import json
import asyncio
import re
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import datetime
from scheduling import schedule_task, send_message
import os
from telethon import TelegramClient, errors

from dotenv import load_dotenv

from telethon.sessions import StringSession



# Configuración inicial
DATA_FILE = 'cupets.json'

def save_data():
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

# Cargar o inicializar datos
try:
    with open(DATA_FILE, 'r') as file:
        data = json.load(file)
    # Asegurar que siempre existan las claves principales
    if 'cupets' not in data:
        data['cupets'] = []
    if 'users' not in data:
        data['users'] = []
except FileNotFoundError:
    data = {
        "cupets": [],
        "users": [
            {
                "username": "frankperez24",
                "is_admin": True,
                "api_id": "12345",
                "api_hash": "abcdef123456",
                "scheduled_turnos": [],
                "scheduled_envios": []
            }
        ]
    }
    save_data()



# Funciones de verificación
def is_registered(username):
    return any(u['username'] == username for u in data['users'])

def is_admin(username):
    user = next((u for u in data['users'] if u['username'] == username), None)
    return user and user.get('is_admin', False)

load_dotenv() 

# Inicialización del bot
API_TOKEN = os.getenv('API_TOKEN', '')
bot = Bot(token=API_TOKEN)
router = Router()

# Estados FSM
class Form(StatesGroup):
    waiting_for_cupet_name = State()
    waiting_for_cupet_username = State()
    waiting_for_turno_description = State()
    waiting_for_turno_chapa = State()
    waiting_for_edit_name = State()
    waiting_for_edit_username = State()
    waiting_for_schedule_time = State()
    waiting_for_schedule_chapa = State()
    waiting_for_new_user_username = State()
    waiting_for_new_user_phone = State()
    waiting_for_new_user_api_id = State()
    waiting_for_new_user_api_hash = State()
    waiting_for_edit_turno_time = State()
    waiting_for_edit_turno_chapa = State()


# Teclados
def menu_principal(user_username):
    if is_admin(user_username):
        return types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text='👤 Añadir Usuario', callback_data='add_user')],
            [types.InlineKeyboardButton(text='📋 Gestionar Cupets', callback_data='manage_cupets')],
            [types.InlineKeyboardButton(text='🔁 Gestionar Turnos', callback_data='manage_turnos')],
            [types.InlineKeyboardButton(text='⏰ Programar envio de chapa', callback_data='schedule_turno')]
        ])
    else:
        return types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text='🔁 Gestionar Turnos', callback_data='manage_turnos')],
            [types.InlineKeyboardButton(text='⏰ Programar envio de chapa', callback_data='schedule_turno')]
        ])

def menu_gestion_cupets():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='📋 Listar Cupets', callback_data='list_cupets')],
        [types.InlineKeyboardButton(text='➕ Añadir Cupet', callback_data='add_cupet')],
        [types.InlineKeyboardButton(text='🔙 Volver al Menú', callback_data='back_to_main')]
    ])

def opciones_cupet(username):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text='✏️ Editar Nombre', callback_data=f'edit_cupet_name:{username}')],
        [types.InlineKeyboardButton(text='🔗 Editar Usuario', callback_data=f'edit_cupet_username:{username}')],
        [types.InlineKeyboardButton(text='❌ Eliminar Cupet', callback_data=f'remove_cupet:{username}')],
        [types.InlineKeyboardButton(text='🔙 Volver', callback_data='manage_cupets')]
    ])

def menu_gestion_turnos(turnos):
    keyboard = []
    for index, turno in enumerate(turnos):
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"{turno['chapa']} (@{turno['cupet_username']}) | {turno['descripcion']}",
                callback_data=f"view_turno:{index}"
            ),
            types.InlineKeyboardButton(
                text="❌",
                callback_data=f"delete_turno:{index}"
            )
        ])
    keyboard.append([
        types.InlineKeyboardButton(text='➕ Añadir Turno', callback_data='add_turno'),
        types.InlineKeyboardButton(text='🔙 Volver', callback_data='back_to_main')
    ])
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def menu_gestion_envios(envios):
    keyboard = []
    for index, envio in enumerate(envios):
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"{envio['time']} - {envio['chapa']}",
                callback_data=f"view_envio:{index}"
            ),
            types.InlineKeyboardButton(
                text="❌",
                callback_data=f"cancel_envio:{index}"
            )
        ])
    keyboard.append([
        types.InlineKeyboardButton(text='🔙 Volver', callback_data='back_to_main')
    ])
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

# Handlers principales
@router.message(Command('start'))
async def comando_inicio(message: types.Message, state: FSMContext):
    user = message.from_user
    if not user.username:
        await message.answer("Por favor, configura un nombre de usuario en Telegram para usar este bot.")
        return
    
    if not is_registered(user.username):
        await message.answer("Para poder comenzar a usar el bot contacta a @frankperez24")
        return
    
    user_data = next((u for u in data['users'] if u['username'] == user.username), None)
    if not user_data:
        await message.answer("Error: usuario no encontrado en los registros.")
        return
    try:
        # Define a custom directory for session files
        session_dir = "telethon_sessions"
        os.makedirs(session_dir, exist_ok=True)  # Create the directory if it doesn't exist

        # Create a session file path
        session_name = f"session_{user_data['api_id']}"
        session_path = os.path.join(session_dir, session_name)
        
        client = TelegramClient(session_path, user_data['api_id'], user_data['api_hash'])
        await client.connect()
        await client.start()
        await message.answer('¡Bienvenido! Selecciona una opción:', reply_markup=menu_principal(user.username))
        await client.disconnect()
    except Exception as e:
        print("Error: ", e)
        return

@router.callback_query(F.data == 'back_to_main')
async def volver_menu_principal(callback: types.CallbackQuery):
    await callback.message.edit_text('Menú Principal:', reply_markup=menu_principal(callback.from_user.username))

# Handlers de gestión de usuarios
@router.callback_query(F.data == 'add_user')
async def start_add_user(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.username):
        await callback.answer("Acceso denegado", show_alert=True)
        return
    
    await state.set_state(Form.waiting_for_new_user_phone)
    await callback.message.answer("📱 Envía el número de teléfono del nuevo usuario (incluye el código de país, sin espacios):")

@router.message(Form.waiting_for_new_user_phone)
async def get_new_user_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(Form.waiting_for_new_user_username)
    await message.answer("👤 Ahora envía el nombre de usuario del nuevo usuario (sin @):")

@router.message(Form.waiting_for_new_user_username)
async def get_new_user_username(message: types.Message, state: FSMContext):
    if is_registered(message.text):
        await message.answer("❌ Este usuario ya está registrado")
        return
    
    await state.update_data(username=message.text)
    await state.set_state(Form.waiting_for_new_user_api_id)
    await message.answer("🔢 Envía el API ID del usuario:")

@router.message(Form.waiting_for_new_user_api_id)
async def get_new_user_api_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ El API ID debe ser numérico")
        return
    
    await state.update_data(api_id=message.text)
    await state.set_state(Form.waiting_for_new_user_api_hash)
    await message.answer("Envía el API HASH del usuario:")

@router.message(Form.waiting_for_new_user_api_hash)
async def get_new_user_api_hash(message: types.Message, state: FSMContext):
    data_user = await state.get_data()
    
    new_user = {
        "username": data_user['username'],
        "phone": data_user['phone'],
        "api_id": data_user['api_id'],
        "api_hash": message.text,
        "is_admin": False,
        "scheduled_turnos": []
    }
    
    data['users'].append(new_user)
    save_data()
    
    await message.answer(f"✅ Usuario @{data_user['username']} registrado exitosamente!")
    await state.clear()

@router.callback_query(F.data == 'back_to_main')
async def volver_menu_principal(callback: types.CallbackQuery):
    await callback.message.edit_text('Menú Principal:', reply_markup=menu_principal(callback.from_user.username))


# Handlers de Cupets (solo admin)
@router.callback_query(F.data == 'manage_cupets')
async def manage_cupets(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.username):
        await callback.answer("Acceso denegado", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📋 Menú de Gestión de Cupets:",
        reply_markup=menu_gestion_cupets()
    )

@router.callback_query(F.data == 'list_cupets')
async def listar_cupets(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.username):
        await callback.answer("Acceso denegado", show_alert=True)
        return
    
    if not data['cupets']:
        await callback.message.edit_text('No hay Cupets registrados.', reply_markup=menu_gestion_cupets())
        return

    botones = [[types.InlineKeyboardButton(text=f"{c['name']} (@{c['username']})", callback_data=f'cupet_options:{c["username"]}')] for c in data['cupets']]
    botones.append([types.InlineKeyboardButton(text='🔙 Volver', callback_data='manage_cupets')])
    await callback.message.edit_text(
        '📋 Lista de Cupets:',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=botones)
    )

@router.callback_query(F.data.startswith('cupet_options:'))
async def cupet_options_handler(callback: types.CallbackQuery):
    username = callback.data.split(':')[1]
    await callback.message.edit_text(
        f"Opciones para @{username}:",
        reply_markup=opciones_cupet(username)
    )

@router.callback_query(F.data == 'add_cupet')
async def iniciar_creacion(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.username):
        await callback.answer("Acceso denegado", show_alert=True)
        return
    
    await state.set_state(Form.waiting_for_cupet_name)
    await callback.message.edit_text('Envía el nombre del nuevo Cupet:')

@router.message(Form.waiting_for_cupet_name)
async def recibir_nombre(message: types.Message, state: FSMContext):
    await state.update_data(nombre=message.text)
    await state.set_state(Form.waiting_for_cupet_username)
    await message.answer('Ahora envía el nombre de usuario único (ej: @cupetgroup):')

@router.message(Form.waiting_for_cupet_username)
async def recibir_usuario(message: types.Message, state: FSMContext):
    datos = await state.get_data()
    username = message.text.strip()
    
    if any(c['username'] == username for c in data['cupets']):
        await message.answer('❌ Este usuario ya existe. Elige otro nombre.')
        return
    
    data['cupets'].append({
        "name": datos['nombre'],
        "username": username,
        "turnos": []
    })
    save_data()
    await state.clear()
    await message.answer(f'✅ Cupet "{datos["nombre"]}" añadido exitosamente!', reply_markup=menu_principal(message.from_user.username))

@router.callback_query(F.data.startswith('edit_cupet_name:'))
async def editar_nombre_cupet(callback: types.CallbackQuery, state: FSMContext):
    username = callback.data.split(':')[1]
    await state.update_data(old_username=username)
    await state.set_state(Form.waiting_for_edit_name)
    await callback.message.answer("Envía el nuevo nombre para este Cupet:")

@router.message(Form.waiting_for_edit_name)
async def actualizar_nombre_cupet(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cupet = next((c for c in data['cupets'] if c['username'] == data['old_username']), None)
    
    if cupet:
        cupet['name'] = message.text
        save_data()
        await message.answer("✅ Nombre actualizado correctamente!", reply_markup=menu_principal(message.from_user.username))
    await state.clear()

@router.callback_query(F.data.startswith('edit_cupet_username:'))
async def editar_usuario_cupet(callback: types.CallbackQuery, state: FSMContext):
    old_username = callback.data.split(':')[1]
    await state.update_data(old_username=old_username)
    await state.set_state(Form.waiting_for_edit_username)
    await callback.message.answer("Envía el nuevo usuario único para este Cupet:")

@router.message(Form.waiting_for_edit_username)
async def actualizar_usuario_cupet(message: types.Message, state: FSMContext):
    data = await state.get_data()
    new_username = message.text.strip()
    
    if any(c['username'] == new_username for c in data['cupets']):
        await message.answer("❌ Este usuario ya está en uso")
        return
    
    cupet = next((c for c in data['cupets'] if c['username'] == data['old_username']), None)
    if cupet:
        cupet['username'] = new_username
        save_data()
        await message.answer("✅ Usuario actualizado correctamente!", reply_markup=menu_principal(message.from_user.username))
    await state.clear()

@router.callback_query(F.data.startswith('remove_cupet:'))
async def eliminar_cupet(callback: types.CallbackQuery):
    username = callback.data.split(':')[1]
    data['cupets'] = [c for c in data['cupets'] if c['username'] != username]
    save_data()
    await callback.message.answer("✅ Cupet eliminado exitosamente!")
    await listar_cupets(callback)


# Handlers de Turnos
@router.callback_query(F.data == 'manage_turnos')
async def handle_manage_turnos(callback: types.CallbackQuery):
    user = next((u for u in data['users'] if u['username'] == callback.from_user.username), None)
    if not user:
        await callback.answer("Usuario no encontrado")
        return
    
    # Obtener todos los Cupets únicos con turnos
    cupets = list({t['cupet_username'] for t in user['scheduled_turnos'] if 'cupet_username' in t})
    
    if not cupets:
        await callback.message.edit_text(
            "No tienes turnos programados.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text='➕ Añadir Turno', callback_data='add_turno')],
                [types.InlineKeyboardButton(text='🔙 Volver', callback_data='back_to_main')]
            ])
        )
        return
    
    # Crear botones para cada Cupet
    botones = [[types.InlineKeyboardButton(
        text=f" {list(filter(lambda cupet: cupet['username'] == cupet_username, data['cupets']))[0]['name']}", 
        callback_data=f'select_cupet_turnos:{cupet_username}'
    )] for cupet_username in cupets]
    
    botones.append([types.InlineKeyboardButton(text='🔙 Volver', callback_data='back_to_main')])
    
    await callback.message.edit_text(
        "📋 Selecciona un Cupet para gestionar sus turnos:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=botones)
    )

@router.callback_query(F.data.startswith('select_cupet_turnos:'))
async def handle_select_cupet_turnos(callback: types.CallbackQuery):
    cupet_username = callback.data.split(':')[1]
    user = next((u for u in data['users'] if u['username'] == callback.from_user.username), None)
    
    if not user:
        await callback.answer("Usuario no encontrado")
        return
    
    # Obtener turnos con sus índices originales
    turnos_con_indices = [
        (idx, t) for idx, t in enumerate(user['scheduled_turnos']) 
        if t.get('cupet_username') == cupet_username
    ]
    
    if not turnos_con_indices:
        await callback.message.edit_text(
            f"No hay turnos en @{cupet_username}",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text='🔙 Volver', callback_data='manage_turnos')]
            ])
        )
        return
    
    # Crear menú con índices originales
    keyboard = []
    for idx, turno in turnos_con_indices:
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"📝 {turno['descripcion']}",
                callback_data=f"view_turno:{idx}"
            ),
            types.InlineKeyboardButton(
                text=f"🚗 {turno['chapa']}",
                callback_data=f"view_turno:{idx}"
            ),
            types.InlineKeyboardButton(
                text="Borrar",
                callback_data=f"delete_turno:{cupet_username}:{idx}"
            )
        ])
    
    keyboard.append([types.InlineKeyboardButton(text='🔙 Volver', callback_data='manage_turnos')])
    
    await callback.message.edit_text(
        f"📋 Turnos en @{cupet_username}:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data == 'add_turno')
async def start_add_turno(callback: types.CallbackQuery, state: FSMContext):
    if not data['cupets']:
        await callback.message.edit_text('Primero debes crear al menos un Cupet.', reply_markup=menu_principal(callback.from_user.username))
        return

    botones = [[types.InlineKeyboardButton(text=c['name'], callback_data=f'select_cupet_turno:{c["username"]}')] for c in data['cupets']]
    botones.append([types.InlineKeyboardButton(text='🔙 Cancelar', callback_data='back_to_main')])
    await callback.message.edit_text(
        '📋 Selecciona un Cupet para el turno:',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=botones)
    )

@router.callback_query(F.data.startswith('select_cupet_turno:'))
async def seleccionar_cupet_turno(callback: types.CallbackQuery, state: FSMContext):
    cupet_username = callback.data.split(':')[1]
    await state.update_data(cupet_username=cupet_username)
    await state.set_state(Form.waiting_for_turno_description)
    await callback.message.answer("📝 Envía la descripción del turno:")

@router.message(Form.waiting_for_turno_description)
async def recibir_descripcion_turno(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("🚗 Ahora envía la chapa del vehículo:")
    await state.set_state(Form.waiting_for_turno_chapa)

@router.message(Form.waiting_for_turno_chapa)
async def recibir_chapa_turno(message: types.Message, state: FSMContext):
    print(message.from_user.username)
    user = next((u for u in data['users'] if u['username'] == message.from_user.username), None)
    if not user:
        await message.answer("❌ Error: usuario no encontrado.")
        await state.clear()
        return

    state_data = await state.get_data()
    nuevo_turno = {
        "descripcion": state_data['description'],
        "chapa": message.text.strip(),
        "fecha": datetime.datetime.now().isoformat(),
        "cupet_username": state_data['cupet_username']
    }
    
    user['scheduled_turnos'].append(nuevo_turno)
    save_data()
    
    await message.answer(
        f'✅ Turno registrado exitosamente!\n'
        f'📝 Descripción: {state_data["description"]}\n'
        f'🚗 Chapa: {message.text}\n'
        f'⛽ Cupet: {state_data["cupet_username"]}',
        reply_markup=menu_principal(message.from_user.username)
    )
    await state.clear()

@router.message(Form.waiting_for_turno_description)
async def recibir_descripcion_turno(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(Form.waiting_for_turno_chapa)
    await message.answer("🚗 Ahora envía la chapa del vehículo:")

@router.message(Form.waiting_for_turno_chapa)
async def recibir_chapa_turno(message: types.Message, state: FSMContext):
    user = next((u for u in data['users'] if u['username'] == message.from_user.username), None)
    if not user:
        await message.answer("❌ Error: usuario no encontrado.")
        await state.clear()
        return

    state_data = await state.get_data()
    nuevo_turno = {
        "descripcion": state_data['description'],
        "chapa": message.text.strip(),
        "fecha": datetime.datetime.now().isoformat()
    }
    
    user['scheduled_turnos'].append(nuevo_turno)
    save_data()
    
    await message.answer(
        f'✅ Turno registrado exitosamente!\n'
        f'📝 Descripción: {state_data["description"]}\n'
        f'🚗 Chapa: {message.text}',
        reply_markup=menu_principal(message.from_user.username)
    )
    await state.clear()

@router.callback_query(F.data.startswith('delete_turno:'))
async def delete_turno(callback: types.CallbackQuery):
    _, cupet_username, index = callback.data.split(':')
    index = int(index)
    
    user = next((u for u in data['users'] if u['username'] == callback.from_user.username), None)
    
    if user and 0 <= index < len(user['scheduled_turnos']):
        # Verificar que pertenece al Cupet correcto
        if user['scheduled_turnos'][index].get('cupet_username') == cupet_username:
            deleted = user['scheduled_turnos'].pop(index)
            save_data()
            await callback.message.answer(f"✅ Turno eliminado: {deleted['descripcion']}")
            await handle_select_cupet_turnos(callback)  # Recargar la lista actualizada
        else:
            await callback.answer("❌ El turno no pertenece a este Cupet")
    else:
        await callback.answer("❌ Error al eliminar el turno")

@router.callback_query(F.data.startswith('edit_turno:'))
async def start_edit_turno(callback: types.CallbackQuery, state: FSMContext):
    _, cupet_username, index = callback.data.split(':')
    index = int(index)
    
    user = next((u for u in data['users'] if u['username'] == callback.from_user.username), None)
    
    if user and 0 <= index < len(user['scheduled_turnos']):
        if user['scheduled_turnos'][index].get('cupet_username') == cupet_username:
            await state.update_data(
                cupet_username=cupet_username,
                turno_index=index
            )
            await state.set_state(Form.waiting_for_edit_turno_time)
            await callback.message.answer("Envía la nueva hora (HH:MM:SS):")
        else:
            await callback.answer("❌ El turno no pertenece a este Cupet")
    else:
        await callback.answer("❌ Turno no encontrado")

@router.message(Form.waiting_for_edit_turno_time)
async def edit_turno_time(message: types.Message, state: FSMContext):
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$', message.text):
        await message.answer('❌ Formato inválido. Usa HH:MM:SS')
        return
    
    await state.update_data(new_time=message.text)
    await state.set_state(Form.waiting_for_edit_turno_chapa)
    await message.answer("Envía la nueva chapa:")

@router.message(Form.waiting_for_edit_turno_chapa)
async def edit_turno_chapa(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    turno_index = state_data.get('turno_index')
    new_time = state_data.get('new_time')
    new_chapa = message.text.strip()
    user = next((u for u in data['users'] if u['username'] == message.from_user.username), None)
    
    if user and 0 <= turno_index < len(user['scheduled_turnos']):
        user['scheduled_turnos'][turno_index].update({
            'time': new_time,
            'chapa': new_chapa
        })
        save_data() 
        await message.answer("✅ Turno actualizado correctamente!")
    else:
        await message.answer("❌ Error al actualizar el turno")

    await state.clear()


# Handlers de Envíos Programados
@router.callback_query(F.data == 'schedule_turno')
async def handle_schedule_turno(callback: types.CallbackQuery):
    if not data['cupets']:
        await callback.message.edit_text('Primero debes crear al menos un Cupet.', reply_markup=menu_principal(callback.from_user.username))
        return

    botones = [[types.InlineKeyboardButton(text=c['name'], callback_data=f'select_cupet_schedule:{c["username"]}')] for c in data['cupets']]
    botones.append([types.InlineKeyboardButton(text='🔙 Cancelar', callback_data='back_to_main')])
    await callback.message.edit_text('⏰ Selecciona un Cupet para programar:', reply_markup=types.InlineKeyboardMarkup(inline_keyboard=botones))

@router.callback_query(F.data.startswith('select_cupet_schedule:'))
async def seleccionar_cupet_programacion(callback: types.CallbackQuery, state: FSMContext):
    username = callback.data.split(':')[1]
    await state.update_data(cupet_username=username)
    await state.set_state(Form.waiting_for_schedule_time)
    await callback.message.edit_text('🕒 Envía la hora en formato HH:MM:SS (24 horas)\nEjemplo: 14:30:00')

@router.message(Form.waiting_for_schedule_time)
async def recibir_hora_programacion(message: types.Message, state: FSMContext):
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$', message.text):
        await message.answer('❌ Formato inválido. Usa HH:MM:SS (ej: 14:30:00)')
        return
    
    await state.update_data(time=message.text)
    await message.answer('🚗 Ahora envía la chapa del vehículo:')
    await state.set_state(Form.waiting_for_schedule_chapa)

async def get_login_code(client, timeout=30):
    """Attempt to fetch the OTP code from Telegram messages within a timeout period."""
    end_time = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end_time:
        async for message in client.iter_messages("Telegram"):
            if message.text:
                code_match = re.search(r'(\d{5})', message.text)
                if code_match:
                    return code_match.group(1)
        await asyncio.sleep(2)
    return None

@router.message(Form.waiting_for_schedule_chapa)
async def programar_turno(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    time = state_data.get('time')
    cupet_username = state_data.get('cupet_username')
    chapa = message.text.strip()
    
    user = next((u for u in data['users'] if u['username'] == message.from_user.username), None)
    if not user:
        await message.answer("❌ Error: usuario no encontrado.")
        await state.clear()
        return

    time = state_data.get('time')
    cupet_username = state_data.get('cupet_username')
    
    # Schedule the task
    asyncio.create_task(
        schedule_task(
            time, 
            cupet_username, 
            chapa,
            user["api_id"], 
            user["api_hash"]
        )
    )
    
    await message.answer(
        f'✅ Envío programado para {time} en @{cupet_username}\n'
        f'🚗 Chapa: {chapa}',
        reply_markup=menu_principal(message.from_user.username)
    )
    await state.clear()



@router.callback_query(F.data.startswith('cancel_envio:'))
async def cancel_envio(callback: types.CallbackQuery):
    index = int(callback.data.split(':')[1])
    user = next((u for u in data['users'] if u['username'] == callback.from_user.username), None)
    
    if user and 0 <= index < len(user['scheduled_envios']):
        deleted = user['scheduled_envios'].pop(index)
        save_data()
        await callback.message.answer(f"✅ Envío cancelado: {deleted['time']} - {deleted['chapa']}")
    else:
        await callback.answer("❌ Error al cancelar el envío")

# Handler genérico para acceso no autorizado
@router.callback_query()
async def handle_unauthorized(callback: types.CallbackQuery):
    if not is_registered(callback.from_user.username):
        await callback.answer("Acceso no autorizado", show_alert=True)

# Ejecutar el bot
async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())