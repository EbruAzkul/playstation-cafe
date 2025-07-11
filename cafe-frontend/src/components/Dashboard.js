import React, { useState, useEffect } from 'react';

const Dashboard = () => {
  const [tables, setTables] = useState([]);
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [dialog, setDialog] = useState({ open: false, type: '', tableId: null });
  const [notes, setNotes] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [currentSession, setCurrentSession] = useState(null);
  const [receiptData, setReceiptData] = useState(null); // Fiş detayları için

  const API_BASE_URL = 'http://127.0.0.1:8000/api';

  const loadData = async () => {
    try {
      setApiError(false);
      const responses = await Promise.all([
        fetch(`${API_BASE_URL}/tables/`),
        fetch(`${API_BASE_URL}/tables/dashboard_stats/`),
        fetch(`${API_BASE_URL}/products/by_category/`)
      ]);

      for (let response of responses) {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
      }

      const [tablesData, statsData, productsData] = await Promise.all(
        responses.map(response => response.json())
      );
      
      setTables(tablesData);
      setStats(statsData);
      setCategories(productsData);
      
      if (productsData.length > 0 && !selectedCategory) {
        setSelectedCategory(productsData[0].category.name);
      }
      
    } catch (error) {
      console.error('API Error:', error);
      setApiError(true);
      showSnackbar('Sunucuya bağlanılamadı. Backend çalışıyor mu?', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
    setTimeout(() => setSnackbar({ open: false, message: '', severity: 'success' }), 4000);
  };

  const openDialog = (type, tableId = null) => {
    setDialog({ open: true, type, tableId });
    setNotes('');
    setReceiptData(null);
    
    if (type === 'products' && tableId) {
      const table = tables.find(t => t.id === tableId);
      setCurrentSession(table?.current_session);
      if (categories.length > 0 && !selectedCategory) {
        setSelectedCategory(categories[0].category.name);
      }
    }
  };

  const closeDialog = () => {
    setDialog({ open: false, type: '', tableId: null });
    setNotes('');
    setCurrentSession(null);
    setReceiptData(null);
  };

  const apiCall = async (url, method = 'GET', body = null) => {
    try {
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : null
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'İşlem başarısız');
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  };

  const startSession = async () => {
    try {
      // eslint-disable-next-line no-unused-vars
      const response = await apiCall(`${API_BASE_URL}/tables/${dialog.tableId}/start_session/`, 'POST', { notes });
      showSnackbar('Seans başlatıldı!');
      await loadData();
      closeDialog();
    } catch (error) {
      showSnackbar(error.message, 'error');
    }
  };

  // Sadece seansı durdurur, fiş kesmez
  const stopSession = async () => {
    try {
      const response = await apiCall(`${API_BASE_URL}/tables/${dialog.tableId}/stop_session/`, 'POST');
      showSnackbar(`Seans durduruldu! Toplam süre: ${formatDuration({ duration_minutes: response.duration_minutes })}`);
      await loadData();
      closeDialog();
    } catch (error) {
      showSnackbar(error.message, 'error');
    }
  };

  const addProduct = async (productId) => {
    try {
      // Önce ürün adını bul
      let productName = 'Ürün';
      categories.forEach(cat => {
        cat.products.forEach(product => {
          if (product.id === productId) {
            productName = product.name;
          }
        });
      });

      console.log('🛒 Ürün ekleniyor:', productName, 'ID:', productId, 'Masa:', dialog.tableId);

      // eslint-disable-next-line no-unused-vars
      const response = await apiCall(`${API_BASE_URL}/tables/${dialog.tableId}/add_product/`, 'POST', {
        product_id: productId,
        quantity: 1
      });
      
      console.log('🛒 Add product response:', response);
      
      // Eklenen ürün bilgisini göster
      showSnackbar(`${productName} eklendi!`);
      
      console.log('🔄 Loading data after product add...');
      await loadData();
      
      const updatedTable = tables.find(t => t.id === dialog.tableId);
      console.log('🔄 Updated table after loadData:', updatedTable);
      
      if (updatedTable?.current_session) {
        setCurrentSession(updatedTable.current_session);
        console.log('🔄 Updated current session:', updatedTable.current_session);
      }
    } catch (error) {
      console.error('❌ Add product error:', error);
      showSnackbar(error.message, 'error');
    }
  };

  const removeProduct = async (sessionProductId) => {
    try {
      // Önce ürün adını bul
      let productName = 'Ürün';
      if (currentSession && currentSession.products) {
        const sessionProduct = currentSession.products.find(p => p.id === sessionProductId);
        if (sessionProduct) {
          productName = sessionProduct.product_name;
        }
      }

      // eslint-disable-next-line no-unused-vars
      const response = await apiCall(`${API_BASE_URL}/tables/${dialog.tableId}/remove_product/`, 'POST', {
        session_product_id: sessionProductId
      });
      
      showSnackbar(`${productName} çıkarıldı`);
      await loadData();
      
      const updatedTable = tables.find(t => t.id === dialog.tableId);
      if (updatedTable?.current_session) {
        setCurrentSession(updatedTable.current_session);
      }
    } catch (error) {
      showSnackbar(error.message, 'error');
    }
  };

  const createReceipt = async () => {
    try {
      const response = await apiCall(`${API_BASE_URL}/tables/${dialog.tableId}/create_receipt/`, 'POST');
      
      // Debug: Backend'den gelen veriyi console'a yazdır
      console.log('🧾 Backend Response:', response);
      console.log('🧾 Receipt Data:', JSON.stringify(response, null, 2));
      
      // Fiş detaylarını göster
      setReceiptData(response);
      setDialog({ open: true, type: 'receipt_details', tableId: dialog.tableId });
      
      showSnackbar(`Fiş kesildi: ${response.receipt?.receipt_number || response.receipt_number || 'N/A'}`);
      await loadData();
    } catch (error) {
      showSnackbar(error.message, 'error');
    }
  };

  const resetTable = async () => {
    try {
      await apiCall(`${API_BASE_URL}/tables/${dialog.tableId}/reset_table/`, 'POST');
      showSnackbar('Masa resetlendi');
      await loadData();
      closeDialog();
    } catch (error) {
      showSnackbar(error.message, 'error');
    }
  };

  const formatAmount = (amount) => {
    // String'i sayıya çevir, NaN ise 0 kullan
    const numAmount = parseFloat(amount) || 0;
    return `₺${numAmount.toFixed(2)}`;
  };

  const getProductCount = (session) => {
    console.log('🔍 getProductCount called with session:', session);
    
    if (!session || !session.products) {
      console.log('🔍 No session or no products, returning 0');
      return 0;
    }
    
    const count = session.products.reduce((total, product) => {
      console.log('🔍 Product:', product.product_name, 'Quantity:', product.quantity);
      return total + product.quantity;
    }, 0);
    
    console.log('🔍 Total product count:', count);
    return count;
  };

  const formatDuration = (session) => {
    if (!session) return '0 dk';
    const hours = Math.floor(session.duration_minutes / 60);
    const minutes = session.duration_minutes % 60;
    
    if (hours > 0) {
      return `${hours}s ${minutes}dk`;
    }
    return `${session.duration_minutes}dk`;
  };

  const formatDateTime = (dateTimeString) => {
    if (!dateTimeString) return '';
    const date = new Date(dateTimeString);
    return date.toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f3f4f6',
        fontFamily: 'Arial, sans-serif'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '60px',
            height: '60px',
            border: '4px solid #e5e7eb',
            borderTop: '4px solid #3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 1rem'
          }}></div>
          <h2 style={{ color: '#374151', marginBottom: '0.5rem' }}>Veriler yükleniyor...</h2>
          <p style={{ color: '#6b7280' }}>Backend sunucusuna bağlanılıyor...</p>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#f3f4f6',
      fontFamily: 'Arial, sans-serif'
    }}>
      {/* Header */}
      <header style={{
        backgroundColor: '#2563eb',
        color: 'white',
        padding: '1rem',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{
            fontSize: '1.5rem',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span>🎮</span>
            <span>PlayStation Cafe Yönetimi</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {apiError && (
              <span style={{ 
                backgroundColor: '#ef4444', 
                color: 'white', 
                padding: '0.5rem 1rem', 
                borderRadius: '1rem', 
                fontSize: '0.875rem' 
              }}>
                ❌ API Bağlantı Hatası
              </span>
            )}
            <button 
              style={{
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
              onClick={loadData}
            >
              <span>🔄</span>
              <span>Yenile</span>
            </button>
          </div>
        </div>
      </header>

      {/* API Bağlantı Hatası */}
      {apiError && (
        <div style={{ 
          backgroundColor: '#fef2f2', 
          border: '1px solid #fecaca', 
          color: '#dc2626', 
          padding: '1rem', 
          margin: '1rem', 
          borderRadius: '0.5rem' 
        }}>
          <h3 style={{ fontWeight: 'bold', fontSize: '1.125rem', margin: '0 0 0.5rem 0' }}>
            Backend Sunucusuna Bağlanılamadı
          </h3>
          <p style={{ margin: '0.5rem 0' }}>Lütfen Django backend'in çalıştığından emin olun:</p>
          <pre style={{ 
            margin: '0.5rem 0 0 0', 
            backgroundColor: '#1f2937', 
            color: '#10b981', 
            padding: '0.5rem', 
            borderRadius: '0.25rem', 
            fontSize: '0.875rem' 
          }}>
            cd cafe_backend{'\n'}python manage.py runserver
          </pre>
        </div>
      )}

      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '2rem 1rem'
      }}>
        
        {/* İstatistikler */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          <div style={{
            background: 'linear-gradient(135deg, #3b82f6, #1e40af)',
            color: 'white',
            padding: '1.5rem',
            borderRadius: '0.75rem',
            textAlign: 'center',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
              {stats.total_tables || 0}
            </div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>Toplam Masa</div>
          </div>
          <div style={{
            background: 'linear-gradient(135deg, #10b981, #047857)',
            color: 'white',
            padding: '1.5rem',
            borderRadius: '0.75rem',
            textAlign: 'center',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
              {stats.available_tables || 0}
            </div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>Müsait Masa</div>
          </div>
          <div style={{
            background: 'linear-gradient(135deg, #f59e0b, #d97706)',
            color: 'white',
            padding: '1.5rem',
            borderRadius: '0.75rem',
            textAlign: 'center',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
              {stats.occupied_tables || 0}
            </div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>Dolu Masa</div>
          </div>
          <div style={{
            background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
            color: 'white',
            padding: '1.5rem',
            borderRadius: '0.75rem',
            textAlign: 'center',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
              {formatAmount(stats.today_revenue)}
            </div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>Bugünkü Gelir</div>
          </div>
        </div>

        {/* Masa Başlığı */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginBottom: '1.5rem' 
        }}>
          <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>
            Masa Durumu
          </h2>
          <span style={{ 
            backgroundColor: '#dbeafe', 
            color: '#1e40af', 
            padding: '0.5rem 1rem', 
            borderRadius: '1rem' 
          }}>
            ⏱️ {stats.active_sessions || 0} Aktif Seans
          </span>
        </div>

        {/* Masa Kartları */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '1.5rem'
        }}>
          {tables.map((table) => (
            <div 
              key={table.id}
              style={{
                backgroundColor: 'white',
                borderRadius: '0.75rem',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                overflow: 'hidden',
                ...(table.status === 'occupied' && { border: '3px solid #f59e0b' })
              }}
            >
              {/* Kart Başlığı */}
              <div style={{
                padding: '1rem',
                borderBottom: '1px solid #e5e7eb',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0 }}>
                  {table.name}
                </h3>
                <span style={{
                  padding: '0.25rem 0.75rem',
                  borderRadius: '1rem',
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  color: 'white',
                  backgroundColor: 
                    table.status === 'available' ? '#10b981' :
                    table.status === 'occupied' ? '#f59e0b' : '#ef4444'
                }}>
                  {table.status_display}
                </span>
              </div>

              {/* Masa Bilgileri */}
              <div style={{
                padding: '1rem',
                fontSize: '0.875rem',
                color: '#6b7280'
              }}>
                <div><strong>IP:</strong> {table.playstation_ip}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem' }}>
                  <span><strong>Açma:</strong> {formatAmount(table.opening_fee)}</span>
                  <span><strong>Saatlik:</strong> {formatAmount(table.hourly_rate)}</span>
                </div>
              </div>

              {/* Aktif Seans Bilgileri */}
              {table.current_session && (
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#fef3c7',
                  borderLeft: '4px solid #f59e0b'
                }}>
                  <div style={{
                    fontSize: '0.875rem',
                    fontWeight: 'bold',
                    color: '#92400e',
                    marginBottom: '0.5rem'
                  }}>
                    🎮 Aktif Seans
                  </div>
                  
                  {/* Debug: Session bilgilerini göster */}
                  <div style={{
                    fontSize: '0.7rem',
                    backgroundColor: '#f3f4f6',
                    padding: '0.5rem',
                    borderRadius: '0.25rem',
                    marginBottom: '0.5rem',
                    fontFamily: 'monospace'
                  }}>
                    Debug: Products: {table.current_session.products ? table.current_session.products.length : 'null'} | 
                    Count: {getProductCount(table.current_session)}
                  </div>
                  
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.25rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem' }}>
                      <span style={{ marginRight: '0.25rem' }}>⏱️</span>
                      <span>{formatDuration(table.current_session)}</span>
                    </div>
                    <div style={{ fontSize: '0.875rem', fontWeight: 'bold' }}>
                      {formatAmount(table.current_session.gaming_amount)}
                    </div>
                  </div>

                  {table.current_session.products_amount > 0 && (
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '0.25rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem' }}>
                        <span style={{ marginRight: '0.25rem' }}>🛒</span>
                        <span>{getProductCount(table.current_session)} ürün</span>
                      </div>
                      <div style={{ fontSize: '0.875rem', fontWeight: 'bold' }}>
                        {formatAmount(table.current_session.products_amount)}
                      </div>
                    </div>
                  )}

                  <div style={{ 
                    borderTop: '1px solid #d97706', 
                    paddingTop: '0.5rem', 
                    marginTop: '0.5rem' 
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        fontSize: '0.875rem', 
                        fontWeight: 'bold' 
                      }}>
                        <span style={{ marginRight: '0.25rem' }}>💰</span>
                        <span>TOPLAM</span>
                      </div>
                      <div style={{ fontSize: '1rem', fontWeight: 'bold', color: '#dc2626' }}>
                        {formatAmount(table.current_session.total_amount)}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Aksiyon Butonları */}
              <div style={{ padding: '1rem' }}>
                {table.status === 'available' ? (
                  <button
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      fontWeight: 'bold',
                      backgroundColor: '#10b981',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem'
                    }}
                    onClick={() => openDialog('start', table.id)}
                  >
                    <span>▶️</span>
                    <span>Başlat</span>
                  </button>
                ) : table.status === 'occupied' ? (
                  <div>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '0.5rem',
                      marginBottom: '0.5rem'
                    }}>
                      <button
                        style={{
                          padding: '0.5rem',
                          border: 'none',
                          borderRadius: '0.5rem',
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          backgroundColor: '#3b82f6',
                          color: 'white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '0.25rem'
                        }}
                        onClick={() => openDialog('products', table.id)}
                      >
                        <span>🛒</span>
                        {getProductCount(table.current_session) > 0 && (
                          <span style={{ 
                            backgroundColor: '#ef4444', 
                            color: 'white', 
                            borderRadius: '50%', 
                            width: '20px', 
                            height: '20px', 
                            fontSize: '0.75rem', 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center' 
                          }}>
                            {getProductCount(table.current_session)}
                          </span>
                        )}
                        <span>Ürün</span>
                      </button>
                      <button
                        style={{
                          padding: '0.5rem',
                          border: 'none',
                          borderRadius: '0.5rem',
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          backgroundColor: '#ef4444',
                          color: 'white',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '0.25rem'
                        }}
                        onClick={() => openDialog('stop', table.id)}
                      >
                        <span>⏹️</span>
                        <span>Durdur</span>
                      </button>
                    </div>
                    <button
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        border: 'none',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        backgroundColor: '#8b5cf6',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem'
                      }}
                      onClick={() => openDialog('receipt', table.id)}
                    >
                      <span>🧾</span>
                      <span>Fiş Kes & Tahsil Et</span>
                    </button>
                  </div>
                ) : (
                  <button 
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: 'not-allowed',
                      fontWeight: 'bold',
                      backgroundColor: '#6b7280',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem'
                    }}
                    disabled
                  >
                    <span>⚠️</span>
                    <span>Bakımda</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Snackbar */}
      {snackbar.open && (
        <div style={{
          position: 'fixed',
          bottom: '1rem',
          right: '1rem',
          padding: '1rem 1.5rem',
          borderRadius: '0.5rem',
          color: 'white',
          zIndex: 1000,
          backgroundColor: snackbar.severity === 'error' ? '#ef4444' : '#10b981'
        }}>
          {snackbar.message}
        </div>
      )}

      {/* Seans Başlat Dialog */}
      {dialog.open && dialog.type === 'start' && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%'
          }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', fontWeight: 'bold' }}>
              ▶️ Yeni Seans Başlat
            </h3>
            <textarea
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.5rem',
                minHeight: '100px',
                resize: 'vertical',
                marginBottom: '1rem',
                fontFamily: 'inherit',
                boxSizing: 'border-box'
              }}
              placeholder="Müşteri notları (opsiyonel)..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  backgroundColor: 'white',
                  cursor: 'pointer'
                }}
                onClick={closeDialog}
              >
                İptal
              </button>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  borderRadius: '0.5rem',
                  backgroundColor: '#10b981',
                  color: 'white',
                  cursor: 'pointer'
                }}
                onClick={startSession}
              >
                Seansı Başlat
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Seans Durdur Dialog */}
      {dialog.open && dialog.type === 'stop' && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%'
          }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', fontWeight: 'bold' }}>
              ⏹️ Seansı Durdur
            </h3>
            <div style={{
              backgroundColor: '#fef3c7',
              border: '1px solid #f59e0b',
              color: '#92400e',
              padding: '1rem',
              borderRadius: '0.5rem',
              marginBottom: '1rem'
            }}>
              Bu seansı durdurmak istediğinizden emin misiniz?
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 1rem 0' }}>
              <li>• Seans duraklatılacak</li>
              <li>• PlayStation kapatılacak</li>
              <li>• Masa müsait duruma geçecek</li>
              <li>• Fiş kesilmeyecek (daha sonra fiş kesebilirsiniz)</li>
            </ul>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  backgroundColor: 'white',
                  cursor: 'pointer'
                }}
                onClick={closeDialog}
              >
                İptal
              </button>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  borderRadius: '0.5rem',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  cursor: 'pointer'
                }}
                onClick={stopSession}
              >
                Seansı Durdur
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ürün Yönetimi Dialog */}
      {dialog.open && dialog.type === 'products' && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '800px',
            width: '90%',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1.5rem'
            }}>
              <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 'bold' }}>
                🛒 Ürün Yönetimi
              </h3>
              <span style={{
                backgroundColor: '#dbeafe',
                color: '#1e40af',
                padding: '0.5rem 1rem',
                borderRadius: '1rem',
                fontSize: '0.875rem'
              }}>
                {getProductCount(currentSession)} Ürün
              </span>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '2rem'
            }}>
              {/* Kategoriler */}
              <div>
                <h4 style={{ margin: '0 0 1rem 0', fontWeight: 'bold' }}>Kategoriler</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {categories.map((cat) => (
                    <button
                      key={cat.category.id}
                      onClick={() => setSelectedCategory(cat.category.name)}
                      style={{
                        padding: '1rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.5rem',
                        backgroundColor: selectedCategory === cat.category.name ? '#dbeafe' : '#f9fafb',
                        cursor: 'pointer',
                        textAlign: 'left',
                        fontWeight: selectedCategory === cat.category.name ? 'bold' : 'normal',
                        color: selectedCategory === cat.category.name ? '#1e40af' : '#374151'
                      }}
                    >
                      {cat.category.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Ürünler */}
              <div>
                <h4 style={{ margin: '0 0 1rem 0', fontWeight: 'bold' }}>Ürünler</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {categories
                    .filter((cat) => cat.category.name === selectedCategory)
                    .flatMap((cat) => cat.products)
                    .map((product) => (
                      <div
                        key={product.id}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '1rem',
                          border: '1px solid #e5e7eb',
                          borderRadius: '0.5rem',
                          backgroundColor: '#f9fafb'
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 'bold' }}>{product.name}</div>
                          <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                            {formatAmount(product.price)}
                          </div>
                        </div>
                        <button
                          onClick={() => addProduct(product.id)}
                          style={{
                            backgroundColor: '#10b981',
                            color: 'white',
                            border: 'none',
                            padding: '0.5rem 1rem',
                            borderRadius: '0.25rem',
                            cursor: 'pointer',
                            fontWeight: 'bold'
                          }}
                        >
                          +
                        </button>
                      </div>
                    ))}
                </div>
              </div>
            </div>

            {/* Sepet */}
            <div style={{ marginTop: '2rem' }}>
              <h4 style={{ margin: '0 0 1rem 0', fontWeight: 'bold' }}>Sepet</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {currentSession?.products?.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '1rem',
                      backgroundColor: '#f3f4f6',
                      borderRadius: '0.5rem'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 'bold' }}>{item.product_name}</div>
                      <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                        {item.quantity} x ₺{parseFloat(item.unit_price || 0).toFixed(2)} = ₺{parseFloat(item.total_price || 0).toFixed(2)}
                      </div>
                    </div>
                    <button
                      onClick={() => removeProduct(item.id)}
                      style={{
                        backgroundColor: '#ef4444',
                        color: 'white',
                        border: 'none',
                        padding: '0.5rem 1rem',
                        borderRadius: '0.25rem',
                        cursor: 'pointer',
                        fontWeight: 'bold'
                      }}
                    >
                      -
                    </button>
                  </div>
                ))}
                {(!currentSession?.products || currentSession.products.length === 0) && (
                  <div style={{
                    textAlign: 'center',
                    padding: '2rem',
                    color: '#6b7280'
                  }}>
                    Sepet boş - Ürün eklemek için kategorilerden seçim yapın
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem' }}>
              <button
                onClick={closeDialog}
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  borderRadius: '0.5rem',
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  cursor: 'pointer'
                }}
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fiş Kes Dialog */}
      {dialog.open && dialog.type === 'receipt' && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%'
          }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', fontWeight: 'bold' }}>
              🧾 Fiş Kes ve Tahsil Et
            </h3>
            <div style={{
              backgroundColor: '#dbeafe',
              border: '1px solid #3b82f6',
              color: '#1e40af',
              padding: '1rem',
              borderRadius: '0.5rem',
              marginBottom: '1rem'
            }}>
              Bu işlem sonunda fiş kesilecek ve masa tahsil edilerek kapatılacaktır.
            </div>
            <p style={{ margin: '0 0 1rem 0' }}>Bu işlemi yapmak istediğinizden emin misiniz?</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  backgroundColor: 'white',
                  cursor: 'pointer'
                }}
                onClick={closeDialog}
              >
                İptal
              </button>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  borderRadius: '0.5rem',
                  backgroundColor: '#8b5cf6',
                  color: 'white',
                  cursor: 'pointer'
                }}
                onClick={createReceipt}
              >
                Fiş Kes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fiş Detayları Dialog */}
      {dialog.open && dialog.type === 'receipt_details' && receiptData && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '600px',
            width: '90%',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            {/* Fiş Başlığı */}
            <div style={{
              textAlign: 'center',
              borderBottom: '2px solid #e5e7eb',
              paddingBottom: '1rem',
              marginBottom: '1.5rem'
            }}>
              <h2 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem', fontWeight: 'bold' }}>
                🧾 FİŞ DETAYLARI
              </h2>
              <div style={{ fontSize: '1.125rem', fontWeight: 'bold', color: '#3b82f6' }}>
                Fiş No: {receiptData.receipt?.receipt_number || 'N/A'}
              </div>
              <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>
                {formatDateTime(receiptData.end_time || new Date())}
              </div>
            </div>

            {/* Masa ve Seans Bilgileri */}
            <div style={{
              backgroundColor: '#f8fafc',
              padding: '1rem',
              borderRadius: '0.5rem',
              marginBottom: '1.5rem'
            }}>
              <h4 style={{ margin: '0 0 0.5rem 0', fontWeight: 'bold', color: '#374151' }}>
                📅 Seans Bilgileri
              </h4>
              <div style={{ fontSize: '0.875rem', lineHeight: '1.6' }}>
                <div><strong>Masa:</strong> {receiptData.table_name || 'Masa'}</div>
                <div><strong>Müşteri:</strong> {receiptData.user_name || 'Müşteri'}</div>
                <div><strong>Başlangıç:</strong> {formatDateTime(receiptData.start_time)}</div>
                <div><strong>Bitiş:</strong> {formatDateTime(receiptData.end_time)}</div>
                <div style={{ color: '#059669', fontWeight: 'bold' }}>
                  <strong>⏰ Toplam Süre:</strong> {formatDuration({ 
                    duration_minutes: receiptData.receipt?.session_data?.duration_minutes || 0 
                  })}
                </div>
              </div>
            </div>

            {/* Masa Ücretleri Detayı */}
            <div style={{
              backgroundColor: '#fef3c7',
              padding: '1rem',
              borderRadius: '0.5rem',
              marginBottom: '1rem',
              border: '1px solid #f59e0b'
            }}>
              <h4 style={{ margin: '0 0 0.75rem 0', fontWeight: 'bold', color: '#92400e' }}>
                🎮 Oyun Ücret Hesabı
              </h4>
              
              {/* Açma Ücreti */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.5rem 0',
                borderBottom: '1px solid #f59e0b'
              }}>
                <div>
                  <div style={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Masa Açma Ücreti</div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>Sabit ücret</div>
                </div>
                <div style={{ fontWeight: 'bold' }}>
                  {formatAmount(receiptData.receipt?.session_data?.opening_fee || 0)}
                </div>
              </div>

              {/* Süre Ücreti */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.5rem 0',
                borderBottom: '1px solid #f59e0b'
              }}>
                <div>
                  <div style={{ fontWeight: 'bold', fontSize: '0.875rem' }}>Oyun Süresi Ücreti</div>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                    {formatDuration({ 
                      duration_minutes: receiptData.receipt?.session_data?.duration_minutes || 0 
                    })} × {formatAmount(receiptData.receipt?.session_data?.hourly_rate || 0)}/saat
                  </div>
                </div>
                <div style={{ fontWeight: 'bold' }}>
                  {formatAmount(
                    Math.max(0, (receiptData.receipt?.session_data?.gaming_amount || 0) - 
                            (receiptData.receipt?.session_data?.opening_fee || 0))
                  )}
                </div>
              </div>

              {/* Oyun Toplamı */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.75rem 0',
                fontWeight: 'bold',
                fontSize: '1rem',
                color: '#92400e'
              }}>
                <span>🎮 Oyun Toplamı:</span>
                <span>{formatAmount(receiptData.receipt?.session_data?.gaming_amount || 0)}</span>
              </div>
            </div>

            {/* Ürün Listesi */}
            {(() => {
              const products = receiptData.receipt?.session_data?.products || [];
              
              return products.length > 0 ? (
                <div style={{
                  backgroundColor: '#f0f9ff',
                  padding: '1rem',
                  borderRadius: '0.5rem',
                  marginBottom: '1rem',
                  border: '1px solid #0ea5e9'
                }}>
                  <h4 style={{ margin: '0 0 1rem 0', fontWeight: 'bold', color: '#0c4a6e' }}>
                    🛒 Satın Alınan Ürünler
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {products.map((product, index) => (
                      <div
                        key={index}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '0.75rem',
                          backgroundColor: 'white',
                          borderRadius: '0.25rem',
                          border: '1px solid #e0f2fe'
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>
                            {product.product_name || product.name || 'Ürün'}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                            {product.quantity || 1} adet × {formatAmount(product.unit_price || product.price || 0)}
                          </div>
                        </div>
                        <div style={{ fontWeight: 'bold', color: '#0c4a6e' }}>
                          {formatAmount(
                            product.total_price || 
                            ((product.quantity || 1) * (product.unit_price || product.price || 0))
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div style={{
                    marginTop: '0.75rem',
                    paddingTop: '0.75rem',
                    borderTop: '1px solid #bae6fd',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontWeight: 'bold',
                    color: '#0c4a6e'
                  }}>
                    <span>🛒 Ürün Toplamı:</span>
                    <span>{formatAmount(receiptData.receipt?.session_data?.products_amount || 0)}</span>
                  </div>
                </div>
              ) : (
                <div style={{
                  backgroundColor: '#f9fafb',
                  padding: '1rem',
                  borderRadius: '0.5rem',
                  marginBottom: '1rem',
                  textAlign: 'center',
                  color: '#6b7280',
                  fontStyle: 'italic'
                }}>
                  Bu seansta ürün satın alınmamıştır.
                </div>
              );
            })()}

            {/* Genel Toplam */}
            <div style={{
              backgroundColor: '#dcfce7',
              padding: '1.5rem',
              borderRadius: '0.5rem',
              border: '2px solid #16a34a',
              marginBottom: '1.5rem'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#15803d' }}>
                  💰 ÖDENECEKBu TUTAR
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#16a34a' }}>
                  {formatAmount(receiptData.receipt?.session_data?.total_amount || 0)}
                </div>
              </div>
              <div style={{ 
                fontSize: '0.875rem', 
                color: '#15803d', 
                marginTop: '0.5rem',
                textAlign: 'center',
                fontWeight: 'bold'
              }}>
                Oyun: {formatAmount(receiptData.receipt?.session_data?.gaming_amount || 0)} + 
                Ürün: {formatAmount(receiptData.receipt?.session_data?.products_amount || 0)}
              </div>
            </div>

            {/* Kapatma Butonu */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
              <button
                onClick={() => {
                  closeDialog();
                  // 1 saniye sonra reset dialogunu aç
                  setTimeout(() => {
                    openDialog('reset', dialog.tableId);
                  }, 1000);
                }}
                style={{
                  padding: '0.75rem 2rem',
                  border: 'none',
                  borderRadius: '0.5rem',
                  backgroundColor: '#16a34a',
                  color: 'white',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '1rem'
                }}
              >
                ✅ Tamam
              </button>
              <button
                onClick={() => window.print()}
                style={{
                  padding: '0.75rem 2rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  backgroundColor: 'white',
                  color: '#374151',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '1rem'
                }}
              >
                🖨️ Yazdır
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Dialog */}
      {dialog.open && dialog.type === 'reset' && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.75rem',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%'
          }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', fontWeight: 'bold' }}>
              🔄 Masa Resetle
            </h3>
            <div style={{
              backgroundColor: '#fef3c7',
              border: '1px solid #f59e0b',
              color: '#92400e',
              padding: '1rem',
              borderRadius: '0.5rem',
              marginBottom: '1rem'
            }}>
              Bu işlem masayı tamamen sıfırlar. Emin misiniz?
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  backgroundColor: 'white',
                  cursor: 'pointer'
                }}
                onClick={closeDialog}
              >
                İptal
              </button>
              <button
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  borderRadius: '0.5rem',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  cursor: 'pointer'
                }}
                onClick={resetTable}
              >
                Resetle
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;