import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  AppBar,
  Toolbar,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Box,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Timer,
  AttachMoney,
  SportsEsports
} from '@mui/icons-material';
import { apiService } from '../services/api';

const Dashboard = () => {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [dialog, setDialog] = useState({ open: false, type: '', tableId: null });
  const [notes, setNotes] = useState('');

  // Tabloları yükle
  const loadTables = async () => {
    try {
      const response = await apiService.getTables();
      setTables(response.data);
    } catch (error) {
      showSnackbar('Masa bilgileri yüklenemedi', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Snackbar göster
  const showSnackbar = (message, severity = 'success') => {
    setSnackbar({ open: true, message, severity });
  };

  // Dialog aç/kapat
  const openDialog = (type, tableId = null) => {
    setDialog({ open: true, type, tableId });
    setNotes('');
  };

  const closeDialog = () => {
    setDialog({ open: false, type: '', tableId: null });
    setNotes('');
  };

  // Seans başlat
  const startSession = async () => {
    try {
      await apiService.startSession(dialog.tableId, notes);
      showSnackbar('Seans başlatıldı!');
      loadTables();
      closeDialog();
    } catch (error) {
      showSnackbar('Seans başlatılamadı', 'error');
    }
  };

  // Seans durdur
  const stopSession = async () => {
    try {
      const response = await apiService.stopSession(dialog.tableId);
      const { total_amount, duration_minutes } = response.data;
      showSnackbar(
        `Seans sonlandırıldı! Süre: ${duration_minutes} dk, Tutar: ₺${total_amount}`
      );
      loadTables();
      closeDialog();
    } catch (error) {
      showSnackbar('Seans sonlandırılamadı', 'error');
    }
  };

  // Masa durumu rengini belirle
  const getStatusColor = (status) => {
    switch (status) {
      case 'available': return 'success';
      case 'occupied': return 'warning';
      case 'maintenance': return 'error';
      default: return 'default';
    }
  };

  // Masa durumu ikonunu belirle
  const getStatusIcon = (status) => {
    switch (status) {
      case 'available': return <SportsEsports />;
      case 'occupied': return <Timer />;
      case 'maintenance': return <Stop />;
      default: return <SportsEsports />;
    }
  };

  // Süre hesaplama
  const formatDuration = (session) => {
    if (!session) return '0 dk';
    return `${session.duration_minutes} dk`;
  };

  // Tutar formatla
  const formatAmount = (amount) => {
    return `₺${parseFloat(amount || 0).toFixed(2)}`;
  };

  useEffect(() => {
    loadTables();
    // Her 30 saniyede bir güncelle
    const interval = setInterval(loadTables, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Container>
        <Typography variant="h6" align="center" style={{ marginTop: 50 }}>
          Yükleniyor...
        </Typography>
      </Container>
    );
  }

  return (
    <>
      {/* AppBar */}
      <AppBar position="static">
        <Toolbar>
          <SportsEsports style={{ marginRight: 16 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            PlayStation Cafe Yönetimi
          </Typography>
          <Button color="inherit" onClick={loadTables}>
            Yenile
          </Button>
        </Toolbar>
      </AppBar>

      {/* Ana İçerik */}
      <Container maxWidth="lg" style={{ marginTop: 20 }}>
        <Typography variant="h4" gutterBottom>
          Masa Durumu
        </Typography>

        <Grid container spacing={3}>
          {tables.map((table) => (
            <Grid item xs={12} sm={6} md={4} key={table.id}>
              <Card elevation={3}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6" component="div">
                      {table.name}
                    </Typography>
                    <Chip
                      icon={getStatusIcon(table.status)}
                      label={table.status_display}
                      color={getStatusColor(table.status)}
                      size="small"
                    />
                  </Box>

                  <Typography color="text.secondary" gutterBottom>
                    IP: {table.playstation_ip}
                  </Typography>

                  <Typography variant="body2" color="text.secondary">
                    Saatlik Ücret: {formatAmount(table.hourly_rate)}
                  </Typography>

                  {table.current_session && (
                    <Box mt={2} p={2} bgcolor="background.paper" borderRadius={1}>
                      <Typography variant="subtitle2" gutterBottom>
                        Aktif Seans:
                      </Typography>
                      <Box display="flex" alignItems="center" mb={1}>
                        <Timer style={{ marginRight: 8, fontSize: 16 }} />
                        <Typography variant="body2">
                          {formatDuration(table.current_session)}
                        </Typography>
                      </Box>
                      <Box display="flex" alignItems="center">
                        <AttachMoney style={{ marginRight: 8, fontSize: 16 }} />
                        <Typography variant="body2">
                          {formatAmount(table.current_session.current_amount)}
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </CardContent>

                <CardActions>
                  {table.status === 'available' ? (
                    <Button
                      size="small"
                      variant="contained"
                      color="success"
                      startIcon={<PlayArrow />}
                      onClick={() => openDialog('start', table.id)}
                      fullWidth
                    >
                      Başlat
                    </Button>
                  ) : table.status === 'occupied' ? (
                    <Button
                      size="small"
                      variant="contained"
                      color="error"
                      startIcon={<Stop />}
                      onClick={() => openDialog('stop', table.id)}
                      fullWidth
                    >
                      Durdur
                    </Button>
                  ) : (
                    <Button size="small" disabled fullWidth>
                      Bakımda
                    </Button>
                  )}
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Dialog - Seans Başlat */}
      <Dialog open={dialog.open && dialog.type === 'start'} onClose={closeDialog}>
        <DialogTitle>Seans Başlat</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Notlar (opsiyonel)"
            type="text"
            fullWidth
            variant="outlined"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Örn: Müşteri bilgileri, özel istekler..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>İptal</Button>
          <Button onClick={startSession} variant="contained" color="success">
            Başlat
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog - Seans Durdur */}
      <Dialog open={dialog.open && dialog.type === 'stop'} onClose={closeDialog}>
        <DialogTitle>Seansı Sonlandır</DialogTitle>
        <DialogContent>
          <Typography>
            Bu seansı sonlandırmak istediğinizden emin misiniz?
            Otomatik olarak ücret hesaplanacak ve PlayStation kapatılacaktır.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>İptal</Button>
          <Button onClick={stopSession} variant="contained" color="error">
            Sonlandır
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default Dashboard;