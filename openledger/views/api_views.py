import logging

from elasticsearch_dsl import Search
from flask import Flask, render_template, request, abort, jsonify, make_response
from flask.views import MethodView
from sqlalchemy import and_, or_, not_, distinct

from openledger import app, forms, licenses, search
from openledger import models, api

log = logging.getLogger(__name__)

API_BASE = '/api/v1/'

class ListAPI(MethodView):

    def get(self, slug):
        lst = api.get_list(slug)
        if not lst:
            abort(404)
        images = [serialize_image(img) for img in lst.images.order_by(models.Image.created_on.desc()).all()]
        return jsonify(title=lst.title,
                       description=lst.description,
                       slug=lst.slug,
                       creator_displayname=lst.creator_displayname,
                       images=images,)

app.add_url_rule(API_BASE + 'list/<slug>', view_func=ListAPI.as_view('list'))

class ListsAPI(MethodView):

    def post(self):
        if not request.form.get('title'):
            return make_response(jsonify(message="'Title' is a required field"), 422)
        lst = api.create_list(request.form.get('title'), request.form.getlist('identifiers'))
        return make_response(jsonify(slug=lst.slug), 201) # FIXME this should probably be a complete URL

    def delete(self):
        # FIXME will need to deal with auth here, we shouldn't allow deletion of
        # owned lists, and maybe should just harvest anon lists that have no activity?
        if not request.form.get('slug'):
            return make_response(jsonify(message="'Slug' is a required field"), 422)
        lst = api.delete_list(request.form.get('slug'))
        if not lst:
            abort(404)
        return make_response(jsonify(), 204)

    def put(self):
        # FIXME same issue as above, don't allow randos to modify other people's lists
        # If 'title' and not 'slug' is supplied, this will be a CREATE as well
        status_code = 422
        if request.form.get('slug'):
            lst = api.update_list(request.form.get('slug'), image_identifiers=request.form.getlist('identifiers'))
            status_code = 200
        else:
            if request.form.get('title'):
                lst = api.create_list(request.form.get('title'), request.form.getlist('identifiers'))
                status_code = 201
            else:
                return make_response(jsonify(message="One of 'slug' or 'title' is required"), 422)
        if not lst:
            abort(status_code)
        return make_response(jsonify(slug=lst.slug), status_code)

app.add_url_rule(API_BASE + 'lists', view_func=ListsAPI.as_view('lists'))

class ListImageAPI(MethodView):
    """Methods that operate against images within lists"""
    def post(self):
        if not request.form.get('slug'):
            return make_response(jsonify(message="'Slug' is a required field"), 422)
        image = api.add_image_to_list(request.form.get('slug'), image_identifier=request.form.get('identifier'))
        if not image:
            abort(404)
        return make_response(jsonify(serialize_image(image)), 201)

app.add_url_rule(API_BASE + 'list/images', view_func=ListImageAPI.as_view('list-images'))

def serialize_image(img):
    """Return a serialization of an image database suitable for use in the API"""
    return {'identifier': img.identifier,
            'title': img.title,
            'url': img.url,
            'creator': img.creator}