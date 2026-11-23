# Maintainer: PaceTea <dimip.2006@gmail.com>
pkgname=rom-cli
pkgver=1.1.1
pkgrel=2
pkgdesc="Browse and download legal ROMs, homebrew and public-domain games from the Internet Archive (ani-cli style)"
arch=('any')
url="https://github.com/Dukeraider2/rom-cli-sd"
license=('GPL3')
depends=('curl' 'jq' 'fzf' 'aria2' 'python')
makedepends=('git')
source=("$pkgname::git+${url}.git#branch=feature/emudeck-retrodeck-integration")
sha256sums=('SKIP')

package() {
    cd "$srcdir/$pkgname"
    install -Dm755 rom-cli "$pkgdir/usr/lib/rom-cli/rom-cli"
    install -Dm644 library-entry.py "$pkgdir/usr/lib/rom-cli/library-entry.py"
    install -d "$pkgdir/usr/lib/rom-cli/library" "$pkgdir/usr/bin"
    install -m644 library/*.py "$pkgdir/usr/lib/rom-cli/library/"
    ln -s ../lib/rom-cli/rom-cli "$pkgdir/usr/bin/rom-cli"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
