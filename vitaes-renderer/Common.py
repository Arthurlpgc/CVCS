from datetime import date, datetime
import time
from flask import Flask, request, abort, send_file
from CurriculumVitae import CurriculumVitae
from Models import *
import Renders
import json
import timestring
from flask_cors import CORS
import pika

def id_gen(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def parse_date(str):
    print(str)
    return timestring.Date(str).date

def get_field_or_none(req, field_name):
    if field_name in req.keys():
        return req[field_name]
    return None

def get_date_field_or_none(req, field_name):
    field = get_field_or_none(req, field_name)
    if field is None:
        return None
    return datetime.strptime(field, '%Y-%m-%d').date()

def get_parse_string(cv_key, item):
    gen_cv_item = cv_key + '('

    for key, value in item.items():
        gen_cv_item = gen_cv_item + "{0}=".format(key)
        if type(value) is dict:
            for in_key, in_value in value.items():
                inside_item = get_parse_string(in_key, in_value)
                gen_cv_item = gen_cv_item + "{0},".format(inside_item)
                break
        elif key[-4:] == "date":
            gen_cv_item = gen_cv_item + "parse_date('{0}'),".format(value)
        elif type(value) is str:
            gen_cv_item = gen_cv_item + "'{0}',".format(value.replace("'","\\'"))
        else:
            gen_cv_item = gen_cv_item + "'{0}',".format(value)

    gen_cv_item = gen_cv_item + ')'

    return gen_cv_item

def parse_item(cv_key, item):
    try:
        cv_item = eval(get_parse_string(cv_key, item))
    except TypeError as err:
        abort(400, err)

    return cv_item

render_map = {
    'awesome-emerald': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-emerald", "section_order": section_order}),
    'awesome-skyblue': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-skyblue", "section_order": section_order}),
    'awesome-red': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-red", "section_order": section_order}),
    'awesome-pink': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-pink", "section_order": section_order}),
    'awesome-orange': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-orange", "section_order": section_order}),
    'awesome-nephritis': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-nephritis", "section_order": section_order}),
    'awesome-concrete': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-concrete", "section_order": section_order}),
    'awesome-darknight': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="awesome", command="xelatex", params={"color": "awesome-darknight", "section_order": section_order}),
    'modern_cv_casual_blue': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "blue", "scale":"0.75", "section_order": section_order, "style": "casual"}),
    'modern_cv_large_blue': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "blue", "scale":"0.9", "section_order": section_order, "style": "casual"}),
    'modern_cv_casual_green': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "green", "scale":"0.75", "section_order": section_order, "style": "casual"}),
    'modern_cv_large_green': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "green", "scale":"0.9", "section_order": section_order, "style": "casual"}),
    'modern_cv_casual_orange': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "orange", "scale":"0.75", "section_order": section_order, "style": "casual"}),
    'modern_cv_large_orange': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "orange", "scale":"0.9", "section_order": section_order, "style": "casual"}),
    'modern_cv_casual_red': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "red", "scale":"0.75", "section_order": section_order, "style": "casual"}),
    'modern_cv_large_red': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "red", "scale":"0.9", "section_order": section_order, "style": "casual"}),
    'modern_cv_casual_purple': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "purple", "scale":"0.75", "section_order": section_order, "style": "casual"}),
    'modern_cv_large_purple': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "purple", "scale":"0.9", "section_order": section_order, "style": "casual"}),
    'modern_cv_casual_grey': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "grey", "scale":"0.75", "section_order": section_order, "style": "casual"}),
    'modern_cv_large_grey': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "grey", "scale":"0.9", "section_order": section_order, "style": "casual"}),
    'modern_cv_casual_black': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "black", "scale":"0.75", "section_order": section_order, "style": "casual"}),
    'modern_cv_large_black': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "black", "scale":"0.9", "section_order": section_order, "style": "casual"}),
    'modern_cv_classic_blue': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "blue", "scale":"0.75", "section_order": section_order, "style": "classic"}),
    'modern_cv_classic_green': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "green", "scale":"0.75", "section_order": section_order, "style": "classic"}),
    'modern_cv_classic_orange': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "orange", "scale":"0.75", "section_order": section_order, "style": "classic"}),
    'modern_cv_classic_red': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "red", "scale":"0.75", "section_order": section_order, "style": "classic"}),
    'modern_cv_classic_purple': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "purple", "scale":"0.75", "section_order": section_order, "style": "classic"}),
    'modern_cv_classic_grey': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "grey", "scale":"0.75", "section_order": section_order, "style": "classic"}),
    'modern_cv_classic_black': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "black", "scale":"0.75", "section_order": section_order, "style": "classic"}),
    'modern_cv_oldstyle_blue': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "blue", "scale":"0.75", "section_order": section_order, "style": "oldstyle"}),
    'modern_cv_oldstyle_green': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "green", "scale":"0.75", "section_order": section_order, "style": "oldstyle"}),
    'modern_cv_oldstyle_orange': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "orange", "scale":"0.75", "section_order": section_order, "style": "oldstyle"}),
    'modern_cv_oldstyle_red': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "red", "scale":"0.75", "section_order": section_order, "style": "oldstyle"}),
    'modern_cv_oldstyle_purple': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "purple", "scale":"0.75", "section_order": section_order, "style": "oldstyle"}),
    'modern_cv_oldstyle_grey': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "grey", "scale":"0.75", "section_order": section_order, "style": "oldstyle"}),
    'modern_cv_oldstyle_black': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "black", "scale":"0.75", "section_order": section_order, "style": "oldstyle"}),
    'modern_cv_banking_blue': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "blue", "scale":"0.75", "section_order": section_order, "style": "banking"}),
    'modern_cv_banking_green': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "green", "scale":"0.75", "section_order": section_order, "style": "banking"}),
    'modern_cv_banking_orange': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "orange", "scale":"0.75", "section_order": section_order, "style": "banking"}),
    'modern_cv_banking_red': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "red", "scale":"0.75", "section_order": section_order, "style": "banking"}),
    'modern_cv_banking_purple': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "purple", "scale":"0.75", "section_order": section_order, "style": "banking"}),
    'modern_cv_banking_grey': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "grey", "scale":"0.75", "section_order": section_order, "style": "banking"}),
    'modern_cv_banking_black': lambda cv, section_order, path: Renders.CvRenderTexToPdf.render(cv, path=path, cvRender=Renders.CvRenderCheetahTemplate, baseFolder="cv_7", command="pdflatex", params={"color": "black", "scale":"0.75", "section_order": section_order, "style": "banking"}),
}

def render_from_cv_dict(req):
    cv = CurriculumVitae()
    ret = ""

    print("REQUEST")

    req_cv = req
    path = None
    if 'path' in req:
        path = req['path']

    render_key = "awesome-emerald"
    section_order = ['work', 'education', 'achievement', 'project', 'academic', 'language', 'skill']
    if 'curriculum_vitae' in req:
        req_cv = req['curriculum_vitae']
        if 'render_key' in req:
            render_key = req['render_key']
        if 'section_order' in req:
            section_order = req['section_order']

    if 'CvHeaderItem' not in req_cv:
        abort(400, "Missing header")

    for cv_key in req_cv.keys():
        req_key = req_cv[cv_key]

        items = []

        if cv_key == 'CvHeaderItem':
            items.append(req_key)
        else:
            items = req_key

        for item in items:
            cv_item = parse_item(cv_key, item)
            cv.add(cv_item)

    path = render_map[render_key](cv, section_order, path)

    return path
