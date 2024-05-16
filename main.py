from PyQt6 import uic, QtWidgets
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer
from datetime import datetime
import sys
import os
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from wind_params import save_params


# базовый класс графиков
class BaseGraph(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        
        self.xdata = []
        self.lines = []
        self.data_sets = []
        self.line_styles = []  # Сохраняем стили линий
        
        grid_color = '#b0b0b0'
        self.axes.grid(True, color=grid_color)
        for spine in self.axes.spines.values():
            spine.set_color(grid_color)
    
    def update_figure(self):
        for line, data in zip(self.lines, self.data_sets):
            line.set_data(self.xdata, data)
        if self.xdata:
            self.axes.set_xlim(0, max(self.xdata) + 1)
            all_data = [item for sublist in self.data_sets for item in sublist]
            self.axes.set_ylim(min(all_data) - 1, max(all_data) + 1)
        self.draw()
    
    def clear_data(self):
        self.xdata = []
        for data in self.data_sets:
            data.clear()
        self.axes.cla()
        self.axes.grid(True, color='#b0b0b0')
        # Пересоздание линий с сохранением стилей
        self.lines = [self.axes.plot([], [], color=style['color'], linestyle=style['linestyle'])[0] for style in self.line_styles]
        self.draw()

    def add_line(self, color, style='-'):
        line, = self.axes.plot([], [], color=color, linestyle=style)
        self.lines.append(line)
        self.data_sets.append([])
        self.line_styles.append({'color': color, 'linestyle': style})
        
# класс графика температуры
class DynamicGraph(BaseGraph):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_line('r', '-')
        self.add_line('b', '--')

    def update_figure(self, x, temp, ideal_temp):
        self.xdata.append(x)
        self.data_sets[0].append(temp)
        self.data_sets[1].append(ideal_temp)
        super().update_figure()

# класс графика объёмов
class MultiVariableGraph(BaseGraph):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_line('g', '-')
        self.add_line('b', '-')
        self.add_line('r', '--')

    def update_figure(self, x, V1, V2, V):
        self.xdata.append(x)
        self.data_sets[0].append(V2)
        self.data_sets[1].append(V)
        self.data_sets[2].append(V1)
        super().update_figure()

# класс графика давления
class PGraph(BaseGraph):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_line('r', '-')
        self.add_line('b', '--')

    def update_figure(self, x, pressure, ideal_pressure):
        self.xdata.append(x)
        self.data_sets[0].append(pressure)
        self.data_sets[1].append(ideal_pressure)
        super().update_figure()

# класса ПИД контроллера (температуры и давления)
class PIDController:
    def __init__(self, kp, ki, kd, set_point):
        self.Kp = kp
        self.Ki = ki
        self.Kd = kd
        self.set_point = set_point
        self.integral = 0
        self.previous_error = 0

    def update(self, current_temperature, dt):
        error = self.set_point - current_temperature
        self.integral += error * dt
        derivative = (error - self.previous_error) / dt
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        self.previous_error = error
        return output



# Загрузка интерфейсов для двух окон
Form1, Window1 = uic.loadUiType("param.ui")
Form2, Window2 = uic.loadUiType("model.ui")
first_window = None
second_window = None




# в первом окне пользователь выбирает значения параметров
def open_first_window(app):
    global first_window
    first_window = Window1()
    form = Form1()
    form.setupUi(first_window)

    def on_click():
        global params
        params = save_params(form) # парметры сохраняются в глобальную переменную "params"
        first_window.close()
        open_second_window(app, params)

    form.pushButton.clicked.connect(on_click)
    first_window.show()





# во втором окне пользователь работает с реактором
def open_second_window(app, params):
    global second_window, form, pid_controller_T, pid_controller_p
    global timer, graph_update_timer, v_time
    second_window = Window2()
    form = Form2()
    form.setupUi(second_window)
    
    # Настройка названий вещества:
    form.label_15.setText(params['name']['reagent_1'])
    form.label_16.setText(params['name']['reagent_2'])
    form.label_20.setText(params['name']['reagent_1'])
    form.label_23.setText(params['name']['reagent_2'])
    
    
    # Настройка скорости модели:
    v_time = form.verticalSlider.value()
    def update_v_time(value):
        global v_time 
        v_time = value
    form.verticalSlider.valueChanged.connect(update_v_time)
    
    
    # Настройка скорость подачи реагента 1:
    form.dial_3.setMinimum(params['v']['reagent_min'])
    form.dial_3.setMaximum(params['v']['reagent_max'])
    form.dial_3.setValue(params['v']['reagent_1'])
    form.label_39.setText(str(form.dial_3.value()))
    form.dial_3.valueChanged.connect(lambda value: form.label_39.setText(str(value)))

    def update_reagent_1(value):
        params['v']['reagent_1'] = value
    form.dial_3.valueChanged.connect(update_reagent_1)
    
    form.label_41.setText(str(int(form.dial_3.value()/params['v']['reagent_max']*100))+'%')
    form.dial_3.valueChanged.connect(lambda value: form.label_41.setText(str(int(value/params['v']['reagent_max']*100))+'%'))
    
    
    # Настройка скорость подачи реагента 2:
    form.dial_4.setMinimum(params['v']['reagent_min'])
    form.dial_4.setMaximum(params['v']['reagent_max'])
    form.dial_4.setValue(params['v']['reagent_2'])
    form.label_40.setText(str(form.dial_4.value()))
    form.dial_4.valueChanged.connect(lambda value: form.label_40.setText(str(value)))

    def update_reagent_2(value):
        params['v']['reagent_2'] = value
    form.dial_4.valueChanged.connect(update_reagent_2)
    
    form.label_42.setText(str(int(form.dial_4.value()/params['v']['reagent_max']*100))+'%')
    form.dial_4.valueChanged.connect(lambda value: form.label_42.setText(str(int(value/params['v']['reagent_max']*100))+'%'))
    
    
    # Настройка скорость слива:
    form.dial_5.setMinimum(params['v']['discharge_min'])
    form.dial_5.setMaximum(params['v']['discharge_max'])
    form.dial_5.setValue(params['v']['discharge'])
    form.label_43.setText(str(form.dial_5.value()))
    form.dial_5.valueChanged.connect(lambda value: form.label_43.setText(str(value)))

    def update_discharge(value):
        params['v']['discharge'] = value
    form.dial_5.valueChanged.connect(update_discharge)
    
    form.label_44.setText(str(int(form.dial_5.value()/params['v']['discharge_max']*100))+'%')
    form.dial_5.valueChanged.connect(lambda value: form.label_44.setText(str(int(value/params['v']['discharge_max']*100))+'%'))    
    
    
    # Настройка скорости мотора:
    form.dial_6.setMinimum(params['v']['mixing_min'])
    form.dial_6.setMaximum(params['v']['mixing_max'])
    form.dial_6.setValue(params['v']['mixing'])
    form.label_53.setText(str(form.dial_6.value()))
    form.dial_6.valueChanged.connect(lambda value: form.label_53.setText(str(value)))

    def update_v_mixing(value):
        params['v']['mixing'] = value
    form.dial_6.valueChanged.connect(update_v_mixing)
    
    form.label_54.setText('v = '+str(int(form.dial_6.value()/params['v']['mixing_max']*100))+'%')
    form.dial_6.valueChanged.connect(lambda value: form.label_54.setText('v = '+str(int(value/params['v']['mixing_max']*100))+'%'))
    
    
    # Настройка температуры:
    form.label_56.setText(str(round(params['T']['ambient'], 1))+' °C')
    form.doubleSpinBox.setMinimum(params['T']['limit_min'])
    form.doubleSpinBox.setMaximum(params['T']['limit_max'])
    form.doubleSpinBox.setValue(params['T']['ideal'])
    def update_T_ideal(value):
        params['T']['ideal'] = value
    form.doubleSpinBox.valueChanged.connect(update_T_ideal)
    
    
    # Настройка давления:
    form.label_58.setText(str(round(params['p']['atmosphere'], 2))+' атм')
    form.doubleSpinBox_2.setMinimum(params['p']['limit_min'])
    form.doubleSpinBox_2.setMaximum(params['p']['limit_max'])
    form.doubleSpinBox_2.setValue(params['p']['ideal'])
    def update_p_ideal(value):
        params['p']['ideal'] = value
    form.doubleSpinBox_2.valueChanged.connect(update_p_ideal)
    
    
    # Инициализация и настройка виджета графика температуры
    global dynamic_graph
    plot_widget = second_window.findChild(QWidget, 'plotWidget')  # Найдите ваш plotWidget
    dynamic_graph = DynamicGraph(parent=plot_widget)
    plot_widget_layout = QVBoxLayout()  # Создайте новый QVBoxLayout
    plot_widget_layout.addWidget(dynamic_graph)
    plot_widget.setLayout(plot_widget_layout)
    
    
    # Инициализация и настройка виджета графика объёма
    global multi_variable_graph
    plot_widget_2 = second_window.findChild(QWidget, 'plotWidget_2')
    multi_variable_graph = MultiVariableGraph(parent=plot_widget_2)
    plot_widget_2_layout = QVBoxLayout()
    plot_widget_2_layout.addWidget(multi_variable_graph)
    plot_widget_2.setLayout(plot_widget_2_layout)
    
    
    # Инициализация и настройка виджета графика объёма
    global p_graph
    plot_widget_3 = second_window.findChild(QWidget, 'plotWidget_3')
    p_graph = PGraph(parent=plot_widget_3)
    plot_widget_3_layout = QVBoxLayout()
    plot_widget_3_layout.addWidget(p_graph)
    plot_widget_3.setLayout(plot_widget_3_layout)
    
    
    
    # Настройка таймера для обновления графиков раз в половину секунды
    graph_update_timer = QTimer(second_window) 
    graph_update_timer.timeout.connect(update_graph)
    graph_update_timer.timeout.connect(update_multi_graph)
    graph_update_timer.timeout.connect(update_p_graph)
    graph_update_timer.start(500)
    
    # Настройка таймера для более быстрого обновления остального функционала 
    timer = QTimer(second_window)
    timer.timeout.connect(update_current_time)
    timer.start(10) 
    
    # обновление таймера при изменении слайдера скорости модели:
    def update_timer_interval():
        global timer, graph_update_timer, v_time
        timer.start(int(10 / v_time))
        graph_update_timer.start(int(500 / v_time))
    form.verticalSlider.valueChanged.connect(update_timer_interval)
    
    
    second_window.show()






start = True
V_1, V_2, V = 0, 0, 0
T, p = None, None
time_elapsed, time_elapsed_V, time_elapsed_p = None, None, None
ind_V = -1
ind_T, ind_p = 0, 0
ind_T_block, ind_p_block, timer_active = False, False, False
ind_add_reagent_1, ind_add_reagent_2, ind_mix, ind_discharge, ind_logic_T, ind_logic_p, ind_end = False, False, False, False, False, False, False


# слот для обработки событий быстрого таймера
def update_current_time():
    global form, df_rep, V_1, V_2, V, T, params, start, time_elapsed, time_elapsed_V, time_elapsed_p, ind_V, ind_T, ind_T_block, ind_p, ind_p_block
    
    if start:
        time_elapsed_V=0
        time_elapsed_p=0
    
    # Обновление метки текущего времени
    current_time = datetime.now().strftime("%H:%M:%S")
    form.label_45.setText(current_time)  
    
    # Обновление метки времени с начала работы)
    global elapsed_time, timer_active
    if (form.checkBox.isChecked() or form.checkBox_2.isChecked() or 
        form.checkBox_3.isChecked() or form.checkBox_4.isChecked() or 
        form.checkBox_5.isChecked() or form.checkBox_7.isChecked()) and not timer_active:
        elapsed_time = 0
        timer_active = True
    if timer_active:
        elapsed_time += 10  # увеличиваем времени на 10 мс каждый вызов функции
        seconds = int(elapsed_time / 1000)
        form.label_55.setText(f"{seconds // 3600:02}:{(seconds // 60) % 60:02}:{seconds % 60:02}")
    if form.checkBox_10.isChecked():
        timer_active = False
        form.checkBox_10.setChecked(False)
        form.label_55.setText('00:00:00')
    
    
    # Обновление объемов (залив реагентов)
    v_reagent_1 = params['v']['reagent_1'] / 6000
    v_reagent_2 = params['v']['reagent_2'] / 6000
    if form.checkBox.isChecked() and (V+v_reagent_1)/params['V']['reactor']*100 < 100:
        V_1 += v_reagent_1
        V += v_reagent_1
        form.label_3.show()
    else:
        form.checkBox.setChecked(False)
        form.label_3.hide()
    if form.checkBox_2.isChecked() and (V+v_reagent_2)/params['V']['reactor']*100 < 100:
        V_2 += v_reagent_2
        V += v_reagent_2
        form.label_9.show()
    else:
        form.checkBox_2.setChecked(False)
        form.label_9.hide()
    
    # Обновление объемов (слив реагентов)
    v_discharge= params['v']['discharge'] / 6000
    if form.checkBox_3.isChecked():
        form.label_8.show()
        if (V-v_discharge)/params['V']['reactor']*100 > 0:
            V_1 -= V_1/V*v_discharge
            V_2 -= V_2/V*v_discharge
            V -= v_discharge
    else:
        form.label_8.hide()
    
    # Предупреждения по V
    if V/params['V']['reactor']*100 < params['V']['reacror_limit_min']:
        form.label_35.setText('Слишком низкий уровень! \nИспользование реактора невозможно.')
        form.label_33.hide()
        form.label_36.show()
        ind_V=-1
    elif V/params['V']['reactor']*100 < params['V']['reacror_warning_min']:
        form.label_35.setText('Низкий уровень! \nИспользование реактора не рекомендуется.')
        form.label_33.show()
        form.label_36.hide()
        ind_V=0
    elif V/params['V']['reactor']*100 > params['V']['reacror_limit_max']:
        form.label_35.setText('Слишком высокий уровень! \nИспользование реактора невозможно.')
        form.label_33.hide()
        form.label_36.show()
        ind_V=-1
    elif V/params['V']['reactor']*100 > params['V']['reacror_warning_max']:
        form.label_35.setText('Высокий уровень! \nИспользование реактора не рекомендуется.')
        form.label_33.show()
        form.label_36.hide()
        ind_V=0
    else:
        form.label_35.setText('Приемлимый уровень! \nИспользование реактора разрешено.')
        form.label_33.hide()
        form.label_36.hide()
        ind_V=1
    

    # Визуализация изменений уровня внутри реактора (изменение геометрии label_7 в зависимости от V(%))
    new_y = 396 - (272 - 3) * (V / params['V']['reactor'])
    new_height = 3 + (272 - 3) * (V / params['V']['reactor'])
    form.label_7.setGeometry(836, int(new_y), 138, int(new_height))  # Предположительные x и width

    # Обновление инфы о заполненности:
    if V > params['V']['reactor']*0.01:
        form.label_47.setText(str(int(V))+' л ('+str(int(V/params['V']['reactor']*100))+' %)')
        form.label_49.setText(str(int(V_1/V*100))+' %')
        form.label_51.setText(str(int(V_2/V*100))+' %')
        form.progressBar.setValue(int(V/params['V']['reactor']*100))
    else:
        form.label_47.setText(str(int(V))+' л ('+str(int(V/params['V']['reactor']*100))+' %)')
        form.label_49.setText('0 %')
        form.label_51.setText('0 %')
        form.progressBar.setValue(int(V/params['V']['reactor']*100))
    
    
    # Перемешивание (работа мотора) (циклическое изменение размеров метки с изображением мотора)
    v_mixing = params['v']['mixing'] / 20
    if form.checkBox_5.isChecked() and (ind_V != -1 and ind_T not in (-2,2)):
        label_46_width = form.label_46.property('width') or 90
        label_46_x = form.label_46.property('x') or 860
        expanding = form.label_46.property('expanding') or False
        width_change = 2 * v_mixing
        x_change = 1 * v_mixing
        if expanding:
            label_46_width += width_change
            label_46_x -= x_change
        else:
            label_46_width -= width_change
            label_46_x += x_change
        # центрирование метки
        label_46_center = 860 + 45
        label_46_x = label_46_center - label_46_width // 2
        if label_46_width <= 1:
            expanding = True
        elif label_46_width >= 90:
            expanding = False
        # реализация вращения мотрора
        form.label_46.setGeometry(int(label_46_x), 310, int(label_46_width), 61)
        form.label_46.setProperty('width', label_46_width)
        form.label_46.setProperty('x', label_46_x)
        form.label_46.setProperty('expanding', expanding)
    elif ind_V == -1 or ind_T in (-2,2):
        form.checkBox_5.setChecked(False)
        form.label_46.setGeometry(860, 310, 90, 61)
        form.label_46.setProperty('width', 90)
        form.label_46.setProperty('x', 860)
        form.label_46.setProperty('expanding', False)
    else:
        form.label_46.setGeometry(860, 310, 90, 61)
        form.label_46.setProperty('width', 90)
        form.label_46.setProperty('x', 860)
        form.label_46.setProperty('expanding', False)
    
    
    # ПИД-контроллер температуры
    global pid_controller_T, dt, T_id, dynamic_graph, time_elapsed
    if start:
        T = params['T']['ambient']
        T_id = params['T']['ideal']
        pid_controller_T = PIDController(kp=0.5, ki=0.1, kd=0.01, set_point=T_id)
        dt = 0.005
        time_elapsed=0
        form.label_5.hide()
        form.label_6.hide()
    # если в процессе работы значение params['T']['ideal'] меняется (например в результате изменения на doubleSpinBox), то ПИД-регулятор переориентируется на новое значение
    if params['T']['ideal'] != T_id:
        T_id = params['T']['ideal']
        pid_controller_T = PIDController(kp=0.5, ki=0.1, kd=0.01, set_point=T_id)
    
    if form.checkBox_4.isChecked() and ind_V != -1:
        output = pid_controller_T.update(T, dt)
        if T + output*dt <= params['T']['limit_min'] or T + output*dt >= params['T']['limit_max']:
            form.checkBox_4.setChecked(False)
            T_id += 0.0000001
            ind_T_block = True
        else:
            ind_T_block = False
            T += output*dt  # имитация изменения температуры
            form.label_56.setText(str(round(T, 1))+' °C')

        # Визуализация характера изменений Т внутри реактора (label_5 - нагрев, label_6 - охлаждение)
        if abs(output) < 0.01 and abs(T-T_id) < 0.05:
            form.label_5.hide()
            form.label_6.hide()
            form.checkBox_4.setChecked(False)
        elif output > 0:
            form.label_5.hide()
            form.label_6.show()
        elif output < 0:
            form.label_5.show()
            form.label_6.hide()
    elif ind_V == -1:
        form.checkBox_4.setChecked(False)
    else:
        form.label_5.hide()
        form.label_6.hide()
        
    
    # Предупреждения по Т
    if T < params['T']['limit_min'] or ind_T_block:
        form.label_60.setText('Слишком низкая температура! \nИспользование реактора невозможно.')
        form.label_63.hide()
        form.label_61.show()
        ind_T=-2
    elif T < params['T']['warning_min']:
        form.label_60.setText('Низкая температура! \nИспользование реактора не рекомендуется.')
        form.label_63.show()
        form.label_61.hide()
        ind_T=-1
    elif T > params['T']['limit_max'] or ind_T_block:
        form.label_60.setText('Слишком высокая температура! \nИспользование реактора невозможно.')
        form.label_63.hide()
        form.label_61.show()
        ind_T=2
    elif T > params['T']['warning_max']:
        form.label_60.setText('Высокая температура! \nИспользование реактора не рекомендуется.')
        form.label_63.show()
        form.label_61.hide()
        ind_T=1
    else:
        form.label_60.setText('Приемлимая температура! \nИспользование реактора разрешено.')
        form.label_63.hide()
        form.label_61.hide()
        ind_T=0
    
    
    # ПИД-контроллер давления
    global pid_controller_p, p, dp, p_id, p_graph
    if start:
        p = params['p']['atmosphere']
        p_id = params['p']['ideal']
        pid_controller_p = PIDController(kp=0.5, ki=0.1, kd=0.01, set_point=p_id)
        start=False
        dp = 0.005
        time_elapsed_p=0
    # если в процессе работы значение params['p']['ideal'] меняется (например в результате изменения на doubleSpinBox), то ПИД-регулятор переориентируется на новое значение
    if params['p']['ideal'] != p_id:
        p_id = params['p']['ideal']
        pid_controller_p = PIDController(kp=0.5, ki=0.1, kd=0.01, set_point=p_id)
    
    if form.checkBox_7.isChecked(): # and ind_V != -1
        output = pid_controller_p.update(p, dp)
        if p + output*dp <= params['p']['limit_min'] or p + output*dp >= params['p']['limit_max']:
            form.checkBox_7.setChecked(False)
            p_id += 0.0000001
            ind_p_block = True
        else:
            ind_p_block = False
            p += output*dp  # Имитация изменения температуры
            form.label_58.setText(str(round(p, 1))+' атм')
        
        # реализация картинок, которые показывают что давление работает
        if abs(output) < 0.01 and abs(p-p_id) < 0.05:
            #form.label_5.hide()
            #form.label_6.hide()
            form.checkBox_7.setChecked(False)
        # elif output > 0:
        #     form.label_5.hide()
        #     form.label_6.show()
        # elif output < 0:
        #     form.label_5.show()
        #     form.label_6.hide()
    # elif ind_V == -1:
    #     form.checkBox_4.setChecked(False)
    # else:
    #     form.label_5.hide()
    #     form.label_6.hide()
    
    
    
    
    # Предупреждения по p
    if p < params['p']['limit_min'] or ind_p_block:
        form.label_69.setText('Слишком низкое давление! \nИспользование реактора невозможно.')
        form.label_71.hide()
        form.label_68.show()
        ind_p=-2
    elif p < params['p']['warning_min']:
        form.label_69.setText('Низкое давление! \nИспользование реактора не рекомендуется.')
        form.label_71.show()
        form.label_68.hide()
        ind_p=-1
    elif p > params['p']['limit_max'] or ind_p_block:
        form.label_69.setText('Слишком высокое давление! \nИспользование реактора невозможно.')
        form.label_71.hide()
        form.label_68.show()
        ind_p=2
    elif p > params['p']['warning_max']:
        form.label_69.setText('Высокое давление! \nИспользование реактора не рекомендуется.')
        form.label_71.show()
        form.label_68.hide()
        ind_p=1
    else:
        form.label_69.setText('Приемлимое давление! \nИспользование реактора разрешено.')
        form.label_71.hide()
        form.label_68.hide()
        ind_p=0
    
    # вывод запретов
    #form.textEdit.clear()  # Очищаем содержимое перед обновлением
    #if ind_V == -1:
    #    form.textEdit.insertPlainText(" * Запрет: перемешивание. Причина: недопустимый уровень.\n")
    #    form.textEdit.insertPlainText(" * Запрет: изменение температуры. Причина: недопустимый уровень.\n")
    #if ind_T == 2:
    #    form.textEdit.insertPlainText(" * Запрет: перемешивание. Причина: недопустимо высокая температуры.\n")
    #    form.textEdit.insertPlainText(" * Запрет: увеличение температуры. Причина: недопустимо высокая температуры.\n")
    #if ind_T == -2:
    #    form.textEdit.insertPlainText(" * Запрет: перемешивание. Причина: недопустимо низкая температуры.\n")
    #    form.textEdit.insertPlainText(" * Запрет: уменьшение температуры. Причина: недопустимо низкая температура.\n")
    #if ind_V != -1 and ind_T not in (-2, 2):
    #    form.textEdit.insertPlainText(" Запретов нет.\n")
    
    
    
    # обновление таблицы отчётов:
    def update_reagent_action(wiget_status, logic_ind_status, text_on, text_off, current_time):
        if not logic_ind_status and wiget_status:
            new_data = [{"Время": current_time, "Действие": text_on, "Статус действия": "Выполнено"}]
        elif logic_ind_status and not wiget_status:
            new_data = [{"Время": current_time, "Действие": text_off, "Статус действия": "Выполнено"}]
        else:
            return None
        return pd.DataFrame(new_data)
    
    global ind_add_reagent_1, ind_add_reagent_2, ind_mix, ind_discharge, ind_logic_T, ind_logic_p, ind_end
    # добавление 1 реагента
    result_df = update_reagent_action(form.checkBox.isChecked(), ind_add_reagent_1,
                                      "Вкл. добавления первого реагента",
                                      "Выкл. добавления первого реагента",
                                      current_time)
    if result_df is not None:
        df_rep = pd.concat([df_rep, result_df], ignore_index=True)
    ind_add_reagent_1 = form.checkBox.isChecked()

    # добавление 2 реагента
    result_df = update_reagent_action(form.checkBox_2.isChecked(), ind_add_reagent_2,
                                      "Вкл. добавления первого реагента",
                                      "Выкл. добавления первого реагента",
                                      current_time)
    if result_df is not None:
        df_rep = pd.concat([df_rep, result_df], ignore_index=True)
    ind_add_reagent_2 = form.checkBox_2.isChecked()
    
    # перемешивание
    result_df = update_reagent_action(form.checkBox_5.isChecked(), ind_mix,
                                      "Вкл. перемешивание",
                                      "Выкл. перемешивание",
                                      current_time)
    if result_df is not None:
        df_rep = pd.concat([df_rep, result_df], ignore_index=True)
    ind_mix = form.checkBox_5.isChecked()
        
    # слив
    result_df = update_reagent_action(form.checkBox_3.isChecked(), ind_discharge,
                                      "Вкл. слив",
                                      "Выкл. слив",
                                      current_time)
    if result_df is not None:
        df_rep = pd.concat([df_rep, result_df], ignore_index=True)
    ind_discharge = form.checkBox_3.isChecked()
    
    # изменение Т
    result_df = update_reagent_action(form.checkBox_4.isChecked(), ind_logic_T,
                                      "Вкл. режим изменения Т",
                                      "Выкл. режим изменения Т",
                                      current_time)
    if result_df is not None:
        df_rep = pd.concat([df_rep, result_df], ignore_index=True)
    ind_logic_T = form.checkBox_4.isChecked()
    
    # изменение p
    result_df = update_reagent_action(form.checkBox_7.isChecked(), ind_logic_p,
                                      "Вкл. режим изменения p",
                                      "Выкл. режим изменения p",
                                      current_time)
    if result_df is not None:
        df_rep = pd.concat([df_rep, result_df], ignore_index=True)
    ind_logic_p = form.checkBox_7.isChecked()
    
    # end
    if not ind_end and form.checkBox_12.isChecked():
        new_data_1 = [{"Время": current_time, "Действие": "Остановка всех процессов. Завершение работы модели.", "Статус действия": "Выполнено"}]
        df_rep = pd.concat([df_rep, pd.DataFrame(new_data_1)], ignore_index=True)
    
    
    
    # сохранить и закрыть
    if form.checkBox_12.isChecked():
        # сохранение данных
        filename = f"{params['name']['exp']}.xlsx"  # название файла
        reports_folder = os.path.join(os.getcwd(), 'Reports')  # путь к папке 'Reports' текущей директории
        if not os.path.exists(reports_folder): # если такой папки не существует, то создаем ее
            os.makedirs(reports_folder)
        path = os.path.join(reports_folder, filename)
        create_excel(path)
        # закрытие окна
        second_window.close()
        QApplication.instance().quit()


# Создание пустого DataFrame
df_rep = pd.DataFrame(columns=["Время", "Действие", "Статус действия"])
# Функция скачивания файла excel
def create_excel(path):
    global df_rep
    df_rep.to_excel(path, index=False)


# прорисовка графика Т
def update_graph():
    global dynamic_graph, T, time_elapsed, params
    if form.checkBox_4.isChecked():
        ideal_temp = params['T']['ideal']
        dynamic_graph.update_figure(time_elapsed, T, ideal_temp)
        time_elapsed += 0.48
    # очистка графика
    if form.checkBox_6.isChecked():
        time_elapsed = 0
        dynamic_graph.clear_data()  
        form.checkBox_6.setChecked(False)

# прорисовка графика V
def update_multi_graph():
    global multi_variable_graph, time_elapsed_V, V, V_1, V_2, params
    if (form.checkBox.isChecked() or form.checkBox_2.isChecked() or form.checkBox_3.isChecked()) and (V > params['V']['reactor']*0.001): # выклчаем запись графика, если резервуар пуст
        multi_variable_graph.update_figure(time_elapsed_V, V, V_1, V_2)
        time_elapsed_V += 0.48
    # очистка графика
    if form.checkBox_8.isChecked():
        time_elapsed_V = 0
        multi_variable_graph.clear_data()
        form.checkBox_8.setChecked(False)


# прорисовка графика p
def update_p_graph():
    global p_graph, p, time_elapsed_p, params
    if form.checkBox_7.isChecked():
        ideal_p = params['p']['ideal']
        p_graph.update_figure(time_elapsed_p, p, ideal_p)
        time_elapsed_p += 0.48
    # очистка графика
    if form.checkBox_9.isChecked():
        time_elapsed_p = 0
        p_graph.clear_data() 
        form.checkBox_9.setChecked(False)





if __name__ == "__main__":
    app = QApplication(sys.argv)
    open_first_window(app)
    sys.exit(app.exec())