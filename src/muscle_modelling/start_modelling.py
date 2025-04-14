try:
    from msk_modelling_python.src.muscle_modelling import hypertrophy

    def main_print(message):
        print('**********************************')
        stars = '*' * (len(message) + 6)
        print(stars)
        print(f'** {message} **') 
        print(stars)

    main_print('Starting muscle modelling...')


except ImportError:
    print('ImportError')
    print(' at the moment only works from the command line')
