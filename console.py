import os
from data_models import Branch, DBSetupConfig, ServiceType
from prepare_db import Validation, main

class Console:
    
    def __init__(self):
        self.configurations: DBSetupConfig = []
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_menu(self):
        while True:
            self.clear_screen()
            print("=== System Konfiguracji Medycznej ===")
            print("1. Dodaj konfigurację")
            print("2. Usuń konfigurację")
            print("3. Pokaż konfiguracje")
            print("4. Rozpocznij skrypt")
            print("5. Wyjdź")
            choice = input("Wybierz opcję: ")
            
            if choice == "1":
                self.add_configuration()
            elif choice == "2":
                self.delete_configuration()
            elif choice == "3":
                self.show_configurations()
            elif choice == "4":
                self.start_script()
            elif choice == "5":
                print("Do widzenia!")
                break
            else:
                print("Nieprawidłowy wybór, spróbuj ponownie.")
                input("Naciśnij Enter, aby kontynuować...")
    
    def add_configuration(self):
        self.clear_screen()
        print("Dodawanie nowej konfiguracji")
        
        # Choose voivodeship
        print("Wybierz województwo:")
        for name, code in Branch.__members__.items():
            print(f"{code.value}. {name}")
        
        while True:
            try:
                voivodeship_int = int(input("Podaj numer województwa (1-16): "))
                voivodeship = str(voivodeship_int).zfill(2)
                if voivodeship in Branch:
                    break
                else:
                    print("Nieprawidłowy numer, spróbuj ponownie.")
            except ValueError:
                print("Proszę podać liczbę.")
        
        # Choose service type
        print("\nDostępne typy usług:")
        max_code_length = max(len(code.value) for code in ServiceType.__members__.values())
        for desc, code in ServiceType.__members__.items():
            print(f"{code.value}:".ljust(max_code_length + 2) + f" {desc}")

        while True:
            service_type = input("Podaj kod usługi: ")
            if service_type in ServiceType:
                break
            else:
                print("Nieprawidłowy kod, spróbuj ponownie.")

        self.configurations.append((Branch(voivodeship), ServiceType(service_type)))
        print("Konfiguracja została dodana!")
        input("Naciśnij Enter, aby kontynuować...")
    
    def delete_configuration(self):
        self.clear_screen()
        if not self.configurations:
            print("Brak zapisanych konfiguracji.")
            input("Naciśnij Enter, aby wrócić...")
            return
        
        print("Lista zapisanych konfiguracji:")
        for idx, (voivodeship, service) in enumerate(self.configurations, 1):
            print(f"{idx}. {voivodeship.name} - {service.name}")
        
        while True:
            try:
                choice = int(input("Podaj numer konfiguracji do usunięcia: "))
                if 1 <= choice <= len(self.configurations):
                    del self.configurations[choice - 1]
                    print("Konfiguracja została usunięta!")
                    break
                else:
                    print("Nieprawidłowy numer, spróbuj ponownie.")
            except ValueError:
                print("Proszę podać liczbę.")
        input("Naciśnij Enter, aby kontynuować...")
    
    def show_configurations(self):
        self.clear_screen()
        if not self.configurations:
            print("Brak zapisanych konfiguracji.")
        else:
            print("Lista zapisanych konfiguracji:")
            for idx, (voivodeship, service) in enumerate(self.configurations, 1):
                print(f"{idx}. {voivodeship.name} - {service.name}")
        input("Naciśnij Enter, aby wrócić...")

    def start_script(self):
        self.clear_screen()

        config_list = []
        for idx, (voivodeship, service) in enumerate(self.configurations, 1):
            config = { "branch": voivodeship.value, "year": 2025, "service_type": service.value }
            config_list.append(config)
        cfgs = Validation.validate_list(config_list, DBSetupConfig)
        main(cfgs)
        input("Naciśnij Enter, aby wrócić...")

if __name__ == "__main__":
    console = Console()
    console.display_menu()
