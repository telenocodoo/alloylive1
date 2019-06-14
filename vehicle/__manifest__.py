# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Vehicle',
    'version' : '0.1',
    'sequence': 165,
    'category': 'Human Resources',
    'website' : 'https://www.odoo.com/page/vehicle',
    'summary' : 'vehicle',
    'description' : """
Vehicle, leasing, insurances, cost
==================================
With this module, Odoo helps you managing all your vehicles, the
contracts associated to those vehicle as well as services, fuel log
entries, costs and many other features necessary to the management 
of your vehicle of vehicle(s)

Main Features
-------------
* Add vehicles to your vehicle
* Manage contracts for vehicles
* Reminder when a contract reach its expiration date
* Add services, fuel log entry, odometer values for all vehicles
* Show all costs associated to a vehicle or to a type of service
* Analysis graph for costs
""",
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/fleet_security.xml',
        'security/ir.model.access.csv',
        'views/fleet_vehicle_model_views.xml',
        'views/fleet_vehicle_views.xml',
        'data/fleet_cars_data.xml',
        'data/fleet_demo.xml',
        'views/partner.xml'
    ,
    ],

    'demo': [],

    'installable': True,
    'application':True,
}
