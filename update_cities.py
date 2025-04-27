from app import create_app, db
from app.models.models import City

def update_cities():
    app = create_app()
    with app.app_context():
        # Update or create Hamburg
        hamburg = City.query.filter_by(name='Hamburg').first()
        if hamburg:
            hamburg.icon_url = 'https://img.icons8.com/color/48/000000/castle.png'
            hamburg.subtitle = 'City of bridges and crossings.'
            db.session.commit()
            print('Updated Hamburg')
        else:
            # Create Hamburg
            hamburg = City(
                name='Hamburg',
                description='Hamburg is a major port city in northern Germany.',
                information_text='<p>Hamburg, the second-largest city in Germany, is home to numerous crossings and bridges.</p>',
                icon_url='https://img.icons8.com/color/48/000000/castle.png',
                subtitle='City of bridges and crossings.'
            )
            db.session.add(hamburg)
            db.session.commit()
            print('Created Hamburg')
            
        # Update Luxembourg
        luxembourg = City.query.filter_by(name='Luxembourg').first()
        if luxembourg:
            luxembourg.icon_url = 'https://img.icons8.com/color/48/000000/luxembourg.png'
            luxembourg.subtitle = 'In the heart of Europe.'
            db.session.commit()
            print('Updated Luxembourg')
        else:
            print('Luxembourg not found')

if __name__ == '__main__':
    update_cities() 