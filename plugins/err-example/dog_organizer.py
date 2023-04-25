from errbot import BotPlugin, botcmd
import re
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time
import threading

class DogHelper(BotPlugin):
    scheduler = None
    scheduled_jobs = {}

    def activate(self):
        super().activate()
        self.dogs = {}
        self.temp_dogs = {}
        self.user_actions = {}

        if DogHelper.scheduler is None:
            DogHelper.scheduler = BackgroundScheduler()
            DogHelper.scheduler.start()

    def deactivate(self):  
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False) 
            self.scheduled_jobs.clear()
        super().deactivate()
    
    @botcmd
    def start(self, msg, args):
        text = ("Привет! Я помощник по уходу за твоим питомцем. "
                "Для начала, нажми /add_dog, чтобы начать добавлять свою собаку в систему.")
        self.send(msg.frm, text)

    @botcmd
    def add_dog(self, msg, args):
        text = ("Введите имя собаки.")
        self.send(msg.frm, text)
        self.user_actions[msg.frm.id] = 'add_dog_name'

    @botcmd
    def add_walkout(self, msg, args):
        user_id = msg.frm
        self.user_actions[str(msg.frm.id)] = 'add_walkouts'
        self.temp_dogs[str(msg.frm.id)] = {'walkout_count': 0, 'walkouts': []}
        return "Введите количество прогулок в день для вашей собаки."
    
    def send_walkout_reminder(self, user_id, dog_name):
        user = self.build_identifier(user_id)
        self.send(user, f"Время выгуливать {dog_name}!")
    
    @botcmd
    def next_step(self, msg, args):
        self.process_step(msg, args)

    def process_step(self, msg, args):
        user_id = msg.frm.id

        if user_id not in self.user_actions:
            self.send(msg.frm, "Извините, я не понимаю. Пожалуйста, начните с команды /add_dog.")
            return 

        action = self.user_actions[user_id]

        if action == 'add_dog_name':
            self.temp_dogs[user_id] = {'name': args}
            self.user_actions[user_id] = 'add_dog_age'
            self.send(msg.frm, f"Отличное имя! Теперь введите возраст собаки. Возраст должен состоять из числа и месяцев/лет")

        elif action == 'add_dog_age':
            age = args
            pattern = r'^([1-9]|[1-2]\d|30)(?:(?:\s+(?:лет|год|года|месяц|месяцев))|(?:\s*[^\w\s]))$'
            if not re.match(pattern, args):
                self.send(msg.frm, "Некорректное значение. Возраст должен состоять из числа и месяцев/лет. "
                                    "Например, 5 месяцев. Примечание: если собаке год или больше, то нужно писать возраст в годах")
                return 

            self.temp_dogs[user_id]['age'] = age
            self.send(msg.frm, f"Возраст собаки: {age}. Теперь введите пол собаки (мужской/женский).")
            self.user_actions[user_id] = 'add_dog_gender'

        elif action == 'add_dog_gender':
            if args.lower() not in ('мужской', 'женский'):
                self.send(msg.frm, "Пожалуйста, введите пол собаки как 'мужской' или 'женский'.")
                return
            
            self.temp_dogs[user_id]['gender'] = args.lower()
            self.send(msg.frm, f"Пол собаки: {args}. Теперь укажите вес собаки в килограммах.")
            self.user_actions[user_id] = 'add_dog_weight'

        elif action == 'add_dog_weight':
            try:
                weight = int(args)
            except ValueError:
                text = "Пожалуйста, введите корректный вес собаки в виде числа (в килограммах)."
                self.send(msg.frm, text)

            self.temp_dogs[user_id]['weight'] = weight
            self.send(msg.frm, f"Вес собаки: {weight} кг. Теперь введите породу собаки.")
            self.user_actions[user_id] = 'add_dog_breed'

        elif action == 'add_dog_breed':
            if not args:
                return "Пожалуйста, введите породу собаки."

            self.temp_dogs[user_id]['breed'] = args
            self._save_dog(user_id)
            self.send(msg.frm, f"Порода собаки: {args}. Собака успешно добавлена!")
            self.send(msg.frm, "Теперь вы можете настроить календарь прогулок с помощью /add_walkout.")
            del self.user_actions[user_id]
           
        elif action == 'edit_dog_property':
            property_name = args.lower()
            if property_name not in ('имя', 'возраст', 'пол', 'вес', 'порода'):
                return "Выберите одно из следующих свойств для редактирования: 'имя', 'возраст', 'пол', 'вес', 'порода'."

            self.user_actions[user_id] = f'edit_dog_{property_name}'
            self.send(msg.frm, f"Введите новое значение для {property_name}.")

        elif action.startswith('edit_dog_'):
            property_name = action.split('_', 2)[-1]
            self.temp_dogs[user_id][property_name] = args
            self._save_dog(user_id)
            self.send(msg.frm, f"Свойство {property_name} успешно изменено на {args}.")
            del self.user_actions[user_id]

        elif action == 'add_walkouts':
            try:
                walkout_count = int(args)
            except ValueError:
                self.send(msg.frm, "Пожалуйста, введите корректное количество прогулок в виде числа.")
                return

            self.temp_dogs[user_id]['walkout_count'] = walkout_count
            self.temp_dogs[user_id]['walkouts'] = []
            self.user_actions[user_id] = 'add_walkout_time'
            self.send(msg.frm, f"Введите время 1-ой прогулки в формате ЧЧ:ММ (например, 09:30).")

        elif action == 'add_walkout_time':
            try:
                walkout_time = datetime.strptime(args, "%H:%M").time()
            except ValueError:
                self.send(msg.frm, "Пожалуйста, введите корректное время прогулки в формате ЧЧ:ММ (например, 09:30).")
                return

            self.temp_dogs[user_id]['walkouts'].append(walkout_time.strftime("%H:%M"))

            dog_name = self.temp_dogs[str(user_id)].get('name', 'Ваша собака')
            job = self.scheduler.add_job(self.send_walkout_reminder, 'interval', args=[str(user_id), dog_name], days=1, start_date=datetime.now().replace(hour=walkout_time.hour, minute=walkout_time.minute, second=0, microsecond=0))
            self.scheduled_jobs[job.id] = job 

            if len(self.temp_dogs[user_id]['walkouts']) < self.temp_dogs[user_id]['walkout_count']:
                next_walkout = len(self.temp_dogs[user_id]['walkouts']) + 1
                self.send(msg.frm, f"Введите время {next_walkout}-ой прогулки в формате ЧЧ:ММ (например, 09:30).")
            else:
                self.send(msg.frm, "Времена прогулок успешно добавлены")
                self.user_actions[user_id] = None
        
        elif action.startswith('edit_walkout'):
            action = action.split("_")
            if len(action) != 3:
                self.send(msg.frm, "Пожалуйста, введите команду в формате: /edit_walkout <имя собаки> <номер прогулки>.")
                return

            try:
                walkout_time = datetime.strptime(args, "%H:%M")
            except ValueError:
                self.send(msg.frm, "Пожалуйста, введите корректное время прогулки в формате ЧЧ:ММ (например, 09:30).")
                return

            dog_name, walkout_index = action[1], int(action[2]) - 1
            dog = self._find_dog_by_name(user_id, dog_name)
            old_walkout = dog['walkouts'][walkout_index]
            dog['walkouts'][walkout_index] = walkout_time.strftime("%H:%M")

            job_id = f"{str(user_id)}_{dog_name}_{walkout_index + 1}"
            old_job = DogHelper.scheduled_jobs[job_id]
            old_job.remove()
            DogHelper.scheduled_jobs[job_id] = DogHelper.scheduler.add_job(self.send_walkout_reminder, 'cron',
                                                                        hour=walkout_time.hour,
                                                                        minute=walkout_time.minute,
                                                                        args=[str(user_id), dog_name],
                                                                        id=job_id)

            self.send(msg.frm, f"Время прогулки {walkout_index + 1} для собаки {dog_name} изменено с {old_walkout} на {dog['walkouts'][walkout_index]}.")
            del self.user_actions[user_id]

    def _save_dog(self, user_id):
        if user_id not in self.dogs:
            self.dogs[user_id] = []

        existing_dog = self._find_dog_by_name(user_id, self.temp_dogs[user_id]['name'])
        if existing_dog is not None:
            self.dogs[user_id].remove(existing_dog)

        self.dogs[user_id].append(self.temp_dogs[user_id])
        del self.temp_dogs[user_id]

    def _find_dog_by_name(self, user_id, name):
        if user_id not in self.dogs:
            return None

        for dog in self.dogs[user_id]:
            if dog['name'] == name:
                return dog

        return None

    def callback_message(self, msg):
        if msg.body.startswith('/'):
            return
        if msg.frm.id in self.user_actions:
            self.process_step(msg, msg.body)

    @botcmd
    def list_dogs(self, msg, args):
        user_id = msg.frm.id
        if user_id not in self.dogs or not self.dogs[user_id]:
            return "У вас пока нет добавленных собак."

        dog_list = "\n".join([f"{index + 1}. {dog['name']}" for index, dog in enumerate(self.dogs[user_id])])
        return f"Список собак:\n{dog_list}\n\nДля просмотра полной информации о собаке введите /dog_info <имя_собаки>."

    @botcmd
    def dog_info(self, msg, args):
        user_id = msg.frm.id
        dog_name = args.strip()
        dog = self._find_dog_by_name(user_id, dog_name)

        if dog is None:
            return f"Собака с именем {dog_name} не найдена."

        dog_info = (
            f"Имя: {dog['name']}\n"
            f"Возраст: {dog['age']}\n"
            f"Пол: {dog['gender']}\n"
            f"Вес: {dog['weight']}\n"
            f"Порода: {dog['breed']}"
        )
        return dog_info
    
    @botcmd
    def walkout_info(self, msg, args):
        user_id = msg.frm.id
        if user_id not in self.dogs:
            self.send(msg.frm, "У вас пока нет добавленных собак.")
            return

        response = "Информация о прогулках:\n"
        for dog in self.dogs[user_id]:
            response += f"{dog['name']}:\n"
            for i, walkout in enumerate(dog['walkouts']):
                response += f"  Прогулка {i + 1}: {walkout}\n"

        self.send(msg.frm, response)

    @botcmd
    def edit_dog(self, msg, args):
        user_id = msg.frm.id
        dog_name = args.strip()
        dog = self._find_dog_by_name(user_id, dog_name)

        if dog is None:
            return f"Собака с именем {dog_name} не найдена."

        self.temp_dogs[user_id] = dog
        self.send(msg.frm, f"Что вы хотите редактировать для собаки {dog_name}? Введите 'имя', 'возраст', 'пол', 'вес' или 'породу'.")
        self.user_actions[user_id] = 'edit_dog_property'

    @botcmd
    def edit_walkout(self, msg, args):
        user_id = msg.frm.id
        if user_id not in self.dogs:
            return "У вас еще нет добавленных собак. Сначала добавьте собаку с помощью /add_dog."

        try:
            dog_name, walkout_index = args.split(" ", 1)
            walkout_index = int(walkout_index) - 1
        except ValueError:
            return "Некорректный формат. Используйте /edit_walkout имя_собаки номер_прогулки"

        dog = self._find_dog_by_name(user_id, dog_name)
        if dog is None:
            return f"Собаки с именем '{dog_name}' не найдено."

        try:
            old_walkout = dog['walkouts'][walkout_index]
        except IndexError:
            return f"Прогулка с индексом {walkout_index + 1} не найдена."

        self.user_actions[user_id] = ('edit_walkout', dog_name, walkout_index)
        return f"Введите новое время прогулки {walkout_index + 1} для собаки {dog_name} в формате ЧЧ:ММ (например, 09:30)."

    @botcmd
    def delete_dog(self, msg, args):
        user_id = msg.frm.id
        dog_name = args.strip()
        dog = self._find_dog_by_name(user_id, dog_name)

        if dog is None:
            return f"Собака с именем {dog_name} не найдена."

        self.dogs[user_id].remove(dog)
        return f"Собака {dog_name} успешно удалена."

    @botcmd
    def helper(self, msg, args):
        help_text = (
            "Доступные команды:\n"
            "/add_dog - добавить собаку\n"
            "/list_dogs - список ваших собак\n"
            "/edit_dog <имя_собаки> - редактировать собаку\n"
            "/edit_walkout - изменить время прогулки\n"
            "/delete_dog <имя_собаки> - удалить собаку\n"
            "/walkout_info - показать список активных прогулок\n"
            "Введите / и выберите команду для выполнения."
        )
        return help_text
    