{
    'name': 'My Flight Helpdesk',
    'version': '18.0.0.1',
    'summary': 'Flight and Hotel Booking Helpdesk',
    'sequence': 10,
    'description': """ Flight and Hotel Booking Helpdesk """,
    'depends': ['base','helpdesk'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/helpdesk_ticket.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}