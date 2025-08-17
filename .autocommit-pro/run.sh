#!/bin/bash
# AutoCommit Pro - Quick Start Script
# Bu script AutoCommit Pro'yu hızlı bir şekilde başlatmanız için hazırlanmıştır.

set -e  # Hata durumunda çık

# Renkli çıktı için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                      🚀 AutoCommit Pro                        ║"
echo "║                   Quick Start Script                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Fonksiyonlar
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Gerekli kontroller
check_requirements() {
    print_info "Gereksinimler kontrol ediliyor..."
    
    # Python kontrolü
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 kurulu değil!"
        exit 1
    fi
    
    # Git kontrolü
    if ! command -v git &> /dev/null; then
        print_error "Git kurulu değil!"
        exit 1
    fi
    
    # Git repository kontrolü
    if [ ! -d ".git" ]; then
        print_error "Bu dizin bir git repository değil!"
        echo "Lütfen önce 'git init' ve 'git remote add origin <url>' komutlarını çalıştırın."
        exit 1
    fi
    
    # Git config kontrolü
    if [ -z "$(git config user.name)" ] || [ -z "$(git config user.email)" ]; then
        print_error "Git kullanıcı bilgileri yapılandırılmamış!"
        echo "Lütfen şu komutları çalıştırın:"
        echo "git config user.name 'Your Name'"
        echo "git config user.email 'your.email@example.com'"
        exit 1
    fi
    
    print_success "Tüm gereksinimler karşılanıyor!"
}

# Python bağımlılıklarını yükle
install_dependencies() {
    print_info "Python bağımlılıkları kontrol ediliyor..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt dosyası bulunamadı!"
        exit 1
    fi
    
    # Virtual environment oluştur (isteğe bağlı)
    if [ "$1" = "--venv" ]; then
        print_info "Virtual environment oluşturuluyor..."
        python3 -m venv venv
        source venv/bin/activate
        print_success "Virtual environment aktif!"
    fi
    
    # Bağımlılıkları yükle
    print_info "Bağımlılıklar yükleniyor..."
    pip install -r requirements.txt --quiet
    print_success "Bağımlılıklar yüklendi!"
}

# Konfigürasyon kontrolü
check_config() {
    print_info "Konfigürasyon kontrol ediliyor..."
    
    if [ ! -f "config.json" ]; then
        print_warning "config.json bulunamadı, oluşturuluyor..."
        python3 main.py --setup
    fi
    
    # API anahtarı kontrolü
    if ! grep -q '"api_key".*[a-zA-Z0-9]' config.json; then
        print_warning "AI API anahtarı yapılandırılmamış!"
        echo "Lütfen şu komutlardan birini çalıştırın:"
        echo "1. python3 main.py --interactive  # İnteraktif kurulum"
        echo "2. config.json dosyasını manuel olarak düzenleyin"
        echo ""
        echo "AI özelliği olmadan devam etmek için Enter'a basın..."
        read -r
    fi
    
    print_success "Konfigürasyon hazır!"
}

# Ana menü
show_menu() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                        Seçenekler                              ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    echo "║  1) 🚀 Otomatik izlemeyi başlat                               ║"
    echo "║  2) ⚙️  İnteraktif kurulum                                     ║"
    echo "║  3) 📊 Sistem durumu                                          ║"
    echo "║  4) 💾 Manuel commit                                          ║"
    echo "║  5) 📤 Manuel push                                            ║"
    echo "║  6) 🛠️  Konfigürasyon düzenle                                 ║"
    echo "║  7) 📋 Logları görüntüle                                      ║"
    echo "║  8) ❌ Çıkış                                                  ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Ana çalıştırma fonksiyonu
run_autocommit() {
    local cmd="$1"
    
    case $cmd in
        "start")
            print_info "AutoCommit Pro başlatılıyor..."
            python main.py --start
            ;;
        "interactive")
            print_info "İnteraktif kurulum başlatılıyor..."
            python main.py --interactive
            ;;
        "status")
            print_info "Sistem durumu kontrol ediliyor..."
            python main.py --status
            ;;
        "commit")
            echo -n "Commit mesajı girin (boş bırakırsanız AI oluşturacak): "
            read -r message
            if [ -n "$message" ]; then
                python main.py --commit "$message"
            else
                python main.py --commit "AI generated"
            fi
            ;;
        "push")
            print_info "Manuel push yapılıyor..."
            python main.py --push
            ;;
        "config")
            print_info "Konfigürasyon dosyası açılıyor..."
            if command -v nano &> /dev/null; then
                nano config.json
            elif command -v vim &> /dev/null; then
                vim config.json
            else
                print_info "config.json dosyasını bir metin editörü ile açın."
            fi
            ;;
        "logs")
            print_info "Log dosyaları:"
            if [ -d "logs" ]; then
                echo "📁 logs/"
                ls -la logs/
                echo ""
                echo "Hangi log dosyasını görüntülemek istiyorsunuz?"
                echo "1) main.log (Tüm loglar)"
                echo "2) error.log (Sadece hatalar)"
                echo "3) logs.json (JSON format)"
                read -r choice
                case $choice in
                    1) tail -f logs/main.log ;;
                    2) tail -f logs/error.log ;;
                    3) tail -f logs/logs.json ;;
                    *) echo "Geçersiz seçim" ;;
                esac
            else
                print_warning "Log dizini bulunamadı. Sistem henüz çalışmamış olabilir."
            fi
            ;;
        *)
            print_error "Bilinmeyen komut: $cmd"
            ;;
    esac
}

# Parametreli çalışma
if [ $# -gt 0 ]; then
    case $1 in
        "--help"|"-h")
            echo "AutoCommit Pro Quick Start Script"
            echo ""
            echo "Kullanım: $0 [seçenek]"
            echo ""
            echo "Seçenekler:"
            echo "  --start        Otomatik izlemeyi başlat"
            echo "  --setup        İnteraktif kurulum"
            echo "  --status       Sistem durumunu göster"
            echo "  --install      Bağımlılıkları yükle"
            echo "  --venv         Virtual environment ile bağımlılık yükle"
            echo "  --check        Sadece gereksinimleri kontrol et"
            echo "  --help, -h     Bu yardımı göster"
            echo ""
            echo "Parametre olmadan çalıştırırsanız interaktif menü açılır."
            exit 0
            ;;
        "--start")
            check_requirements
            check_config
            run_autocommit "start"
            ;;
        "--setup")
            check_requirements
            install_dependencies
            run_autocommit "interactive"
            ;;
        "--status")
            check_requirements
            run_autocommit "status"
            ;;
        "--install")
            install_dependencies
            ;;
        "--venv")
            install_dependencies "--venv"
            ;;
        "--check")
            check_requirements
            check_config
            print_success "Sistem kullanıma hazır!"
            ;;
        *)
            print_error "Bilinmeyen parametre: $1"
            echo "Yardım için: $0 --help"
            exit 1
            ;;
    esac
    exit 0
fi

# İnteraktif menü
while true; do
    check_requirements
    show_menu
    
    echo -n "Seçiminizi yapın (1-8): "
    read -r choice
    
    case $choice in
        1)
            check_config
            run_autocommit "start"
            ;;
        2)
            run_autocommit "interactive"
            ;;
        3)
            run_autocommit "status"
            ;;
        4)
            run_autocommit "commit"
            ;;
        5)
            run_autocommit "push"
            ;;
        6)
            run_autocommit "config"
            ;;
        7)
            run_autocommit "logs"
            ;;
        8)
            print_info "Güle güle! 👋"
            exit 0
            ;;
        *)
            print_error "Geçersiz seçim! Lütfen 1-8 arasında bir sayı girin."
            ;;
    esac
    
    echo ""
    echo "Menüye dönmek için Enter'a basın..."
    read -r
    clear
done
