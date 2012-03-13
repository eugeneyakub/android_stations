# Create your views here.
# -*- coding: utf-8 -*-

from django.utils import simplejson
from django.http import HttpResponse
import os, shutil
from lxml import etree
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
global_path = settings.GLOBAL_PATH

import pam


def _transform_coords(coords):
    c = coords.split(',')
    return {'latitude': c[0], 'longitude': c[1]}

def _name_to_code(name):
    if name == u'АИ-80':
        return '1'
    elif name == u'АИ-92':
        return '2'
    elif name == u'АИ-95':
        return '3'
    elif name == u'АИ-98':
        return '4'
    elif name == u'ДТ':
        return '5'

@csrf_exempt
def get_stations(request):
    try:
    
        if not os.path.exists(global_path):
            os.makedirs(global_path)
            
        #outDirInit = "stations_import/"    
    #    if os.path.exists(outDirInit):
    #        shutil.rmtree(outDirInit)
    #    os.makedirs(outDirInit)
        
        query = simplejson.loads(request.POST.get('stations', None))
        #query = request.POST.get('stations', None)
        user_name = request.POST.get('user_name', None)
        user_password = request.POST.get('user_password', None)
        
        user_name = '**'
        user_password = '**'
        
        if not pam.authenticate(user_name, user_password, 'passwd'):
            return push_response('wrong login or password')
    
        #if query is None or user_name is None or user_password is None :
        #    return push_response('Missing query or user_name or user_password')
        
        user_path = global_path + '/' + user_name + '/pricelists/'        
        if os.path.exists(user_path):
            shutil.rmtree(user_path)
        os.makedirs(user_path)            
        
        roots = {}
        for station in query:
            roots.setdefault(station['oid'], {
              'needs_update': False,
              'salepoints': [],
            })['salepoints'].append({
              'name': station['name'],
              'url': station['pricelist'],
              'address': station['address'],
              'coords': _transform_coords(station['coords']),
              'offers': [{'name': k['name'], 'price': k['price']} for k in station['offers']],
              'id': station['sid']
            })
       
       
        days = ['mon','tue','wed','thu', 'fri','sat', 'sun']       
       
        for oid, item in roots.items():
            outDir = user_path + 'org-%s/' % (oid)
            if os.path.exists(outDir):
                shutil.rmtree(outDir)
            os.makedirs(outDir)
            
            r = etree.Element('pricelists')
            for sp in item['salepoints']:
                pricelist = etree.SubElement(r, 'pricelist')
                name = etree.SubElement(pricelist, 'name')
                name.text = sp['name']
                url = etree.SubElement(pricelist, 'url')
                url.text = sp['url'].split('/')[-1] if sp['url'] else 'price-' + sp['id'] + '.xml'
                
                shops = etree.SubElement(pricelist, 'shops')
                shop = etree.SubElement(shops, 'shop')

                schedule = etree.SubElement(shop, 'schedule')
                
                for d in days:
                    _d = etree.SubElement(schedule, d)
                    work = etree.SubElement(_d, 'work')
                    work.set('start', '8:00')
                    work.set('end', '22:00')

                                
                city = etree.SubElement(shop, 'city')
                city.text = u'Челябинск'
                address = etree.SubElement(shop, 'address')
                address.text = sp['address']
                coord = etree.SubElement(shop, 'coord')
                lat = etree.SubElement(coord, 'latitude')
                lat.text = sp['coords']['latitude']
                lon = etree.SubElement(coord, 'longitude')
                lon.text = sp['coords']['longitude']
                
                ro = etree.Element('offers')
                for of in sp['offers']:
                    offer = etree.SubElement(ro, 'offer')
                    price = etree.SubElement(offer, 'price')
                    price.text = str(of['price'])
                    code = etree.SubElement(offer, 'code')
                    code.set('source', 'neiron')
                    code.text = _name_to_code(of['name'])
                structureXml = open(outDir + url.text, "w")
                structureXml.write(etree.tostring(ro, pretty_print=True, encoding="cp1251"))
                structureXml.close()
                
            structureXml = open(outDir + 'index.xml', "w")
            structureXml.write(etree.tostring(r, pretty_print=True, encoding="cp1251"))
            structureXml.close()
            
        content = simplejson.dumps(roots)
        callback = request.POST.get('callback', None)
        if callback:
            content = "%s(%s)"%(callback, content)
        return HttpResponse(content, mimetype='application/javascript')
    except Exception as e:
        print str(e)
        

@csrf_exempt
def stations_upload(request):
    if request.method == 'POST':
        print request.FILES
        
    return HttpResponse('OK')
    
def push_response(message):
        response = {
            'status'    : 'Error',
            'message'   : message,
        }
        content = simplejson.dumps(response)
        return HttpResponse(content, mimetype='application/javascript')      
