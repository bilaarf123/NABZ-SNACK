/**
 * Nabz Snack Interactive Application Logic
 * Manages Customer Cart, Cashier POS system, and general UI transitions.
 */

// Format Currency to Rupiah (IDR)
function formatRupiah(number) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(number);
}

// Custom Toast Notification System
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        // Create container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show shadow-lg border-0`;
    toast.style.minWidth = '300px';
    toast.style.background = type === 'error' ? 'rgba(220, 53, 69, 0.95)' : 'rgba(76, 166, 121, 0.95)';
    toast.style.color = '#fff';
    toast.style.backdropFilter = 'blur(10px)';
    toast.style.borderRadius = '12px';
    toast.style.marginBottom = '10px';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : 'fa-check-circle'}"></i>
            <div>${message}</div>
        </div>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close" style="font-size: 0.8rem; padding: 1.25rem;"></button>
    `;
    
    document.getElementById('toast-container').appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(toast);
        bsAlert.close();
    }, 4000);
}

// ==========================================
// 1. CUSTOMER SHOPPING CART SYSTEM
// ==========================================
// Cart sekarang 100% berbasis DATABASE (server-side).
// Semua operasi cart (add, update, remove) dilakukan via form POST ke server.
// Tidak ada lagi localStorage cart — data disimpan di tabel carts & cart_items.
// Badge keranjang di navbar di-render oleh server via context_processor.


// ==========================================
// 2. CASHIER POINT OF SALE (POS) SYSTEM
// ==========================================
var posCart = [];

function addPosItem(productId, name, price, stock) {
    if (stock <= 0) {
        showToast('Maaf, stok produk ini habis!', 'error');
        return;
    }
    
    const existing = posCart.find(item => item.id === productId);
    if (existing) {
        if (existing.quantity >= stock) {
            showToast(`Maaf, batas pembelian maksimal adalah ${stock} (stok tersedia)!`, 'error');
            return;
        }
        existing.quantity += 1;
    } else {
        posCart.push({
            id: productId,
            name: name,
            price: parseFloat(price),
            quantity: 1,
            stock: parseInt(stock)
        });
    }
    renderPosCart();
}

function updatePosQuantity(productId, delta) {
    const item = posCart.find(item => item.id === productId);
    if (item) {
        const newQty = item.quantity + delta;
        if (newQty <= 0) {
            posCart = posCart.filter(i => i.id !== productId);
        } else if (newQty > item.stock) {
            showToast(`Maaf, batas pembelian maksimal adalah ${item.stock} (stok tersedia)!`, 'error');
            return;
        } else {
            item.quantity = newQty;
        }
        renderPosCart();
    }
}

function removePosItem(productId) {
    posCart = posCart.filter(item => item.id !== productId);
    renderPosCart();
}

function renderPosCart() {
    const posList = document.getElementById('pos-cart-list');
    const posTotalText = document.getElementById('pos-total');
    const posItemsInput = document.getElementById('pos-items-input');
    const bayarBtn = document.getElementById('pos-submit-btn');
    
    if (!posList) return;
    
    posList.innerHTML = '';
    let total = 0;
    
    if (posCart.length === 0) {
        posList.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted py-4">Belum ada item dipilih. Klik produk di sebelah kiri untuk menambahkan.</td>
            </tr>
        `;
        if (bayarBtn) bayarBtn.disabled = true;
    } else {
        posCart.forEach(item => {
            const subtotal = item.price * item.quantity;
            total += subtotal;
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div class="fw-bold">${item.name}</div>
                    <small class="text-muted">${formatRupiah(item.price)}</small>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="updatePosQuantity(${item.id}, -1)">-</button>
                        <span>${item.quantity}</span>
                        <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2" onclick="updatePosQuantity(${item.id}, 1)">+</button>
                    </div>
                </td>
                <td>${formatRupiah(subtotal)}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-link text-danger" onclick="removePosItem(${item.id})">
                        <i class="fas fa-times-circle"></i>
                    </button>
                </td>
            `;
            posList.appendChild(tr);
        });
        if (bayarBtn) bayarBtn.disabled = false;
    }
    
    if (posTotalText) posTotalText.innerText = formatRupiah(total);
    if (posItemsInput) posItemsInput.value = JSON.stringify(posCart);
}

// ==========================================
// 3. BUY NOW SYSTEM
// ==========================================
var currentBuyNowProduct = null;

function openBuyNowModal(id, name, price, stock) {
    if (stock <= 0) {
        showToast('Maaf, stok produk ini habis!', 'error');
        return;
    }
    
    currentBuyNowProduct = { id, name, price, stock, quantity: 1 };
    
    document.getElementById('buy-now-name').innerText = name;
    document.getElementById('buy-now-price').innerText = formatRupiah(price);
    document.getElementById('buy-now-qty').innerText = 1;
    document.getElementById('buy-now-stock-info').innerText = `Tersedia: ${stock}`;
    updateBuyNowTotal();
    
    document.getElementById('buyNowOverlay').classList.add('active');
}

function closeBuyNowModal() {
    document.getElementById('buyNowOverlay').classList.remove('active');
    currentBuyNowProduct = null;
}

function updateBuyNowQty(delta) {
    if (!currentBuyNowProduct) return;
    
    const newQty = currentBuyNowProduct.quantity + delta;
    if (newQty < 1) return;
    if (newQty > currentBuyNowProduct.stock) {
        showToast(`Maksimal pembelian adalah ${currentBuyNowProduct.stock}!`, 'warning');
        return;
    }
    
    currentBuyNowProduct.quantity = newQty;
    document.getElementById('buy-now-qty').innerText = newQty;
    updateBuyNowTotal();
}

function updateBuyNowTotal() {
    if (!currentBuyNowProduct) return;
    const total = currentBuyNowProduct.price * currentBuyNowProduct.quantity;
    document.getElementById('buy-now-total').innerText = formatRupiah(total);
    
    // Update hidden input for form submission
    const itemArr = [{
        id: currentBuyNowProduct.id,
        name: currentBuyNowProduct.name,
        price: currentBuyNowProduct.price,
        quantity: currentBuyNowProduct.quantity,
        stock: currentBuyNowProduct.stock
    }];
    document.getElementById('buy-now-items').value = JSON.stringify(itemArr);
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    const overlay = document.getElementById('buyNowOverlay');
    if (e.target === overlay) {
        closeBuyNowModal();
    }
});
