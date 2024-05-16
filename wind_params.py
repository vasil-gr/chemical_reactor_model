def save_params(form):
    params = {}
    
    # запись названий реагентов и названия эксперимента
    name = dict()
    name['reagent_1'] = form.lineEdit.text()
    name['reagent_2'] = form.lineEdit_2.text()
    name['exp'] = form.lineEdit_3.text()
    params['name'] = name    
    # запись V
    V = dict()
    V['reactor'] = form.doubleSpinBox.value()
    V['reacror_warning_min'] = form.spinBox.value()
    V['reacror_warning_max'] = form.spinBox_2.value()
    V['reacror_limit_min'] = form.spinBox_3.value()
    V['reacror_limit_max'] = form.spinBox_4.value()
    params['V'] = V
    # запись T
    T = dict()
    T['ambient'] = form.doubleSpinBox_2.value()
    T['ideal'] = form.doubleSpinBox_3.value()
    T['warning_min'] = form.doubleSpinBox_4.value()
    T['warning_max'] = form.doubleSpinBox_6.value()
    T['limit_min'] = form.doubleSpinBox_5.value()
    T['limit_max'] = form.doubleSpinBox_7.value()
    params['T'] = T
    # запись v
    v = dict()
    v['reagent_1'] = form.spinBox_5.value()
    v['reagent_2'] = form.spinBox_6.value()
    v['reagent_min'] = form.spinBox_8.value()
    v['reagent_max'] = form.spinBox_9.value()
    v['discharge'] = form.spinBox_7.value()
    v['discharge_min'] = form.spinBox_10.value()
    v['discharge_max'] = form.spinBox_11.value()
    v['mixing'] = form.spinBox_21.value()
    v['mixing_min'] = form.spinBox_20.value()
    v['mixing_max'] = form.spinBox_19.value()
    params['v'] = v
    # запись p
    p = dict()
    p['atmosphere'] = form.doubleSpinBox_10.value()
    p['ideal'] = form.doubleSpinBox_11.value()
    p['warning_min'] = form.doubleSpinBox_8.value()
    p['warning_max'] = form.doubleSpinBox_13.value()
    p['limit_min'] = form.doubleSpinBox_9.value()
    p['limit_max'] = form.doubleSpinBox_12.value()
    params['p'] = p

    return params