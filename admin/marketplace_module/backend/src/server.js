import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import morgan from 'morgan';
import paymentRoutes from './routes/payments.js';
import webhookRoutes from './routes/webhooks.js';
import paymentService from './services/paymentService.js';

const app = express();
const PORT = process.env.PORT || 3001;

// Security middleware
app.use(helmet());

// CORS configuration
const corsOptions = {
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true,
};
app.use(cors(corsOptions));

// Logging
if (process.env.NODE_ENV !== 'test') {
  app.use(morgan('combined'));
}

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
});
app.use('/api/', limiter);

// Webhook routes MUST come before JSON parser
// Stripe requires raw body for webhook signature verification
app.use('/api/webhooks/stripe', express.raw({ type: 'application/json' }));

// Regular JSON parsing for all other routes
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
  });
});

// API routes
app.use('/api/payments', paymentRoutes);
app.use('/api/webhooks', webhookRoutes);

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Not found',
    path: req.path,
  });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error('Global error handler:', err);

  // Don't leak error details in production
  const isDevelopment = process.env.NODE_ENV === 'development';

  res.status(err.status || 500).json({
    success: false,
    error: isDevelopment ? err.message : 'Internal server error',
    ...(isDevelopment && { stack: err.stack }),
  });
});

// Start server
const server = app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║     WaddleBot Marketplace Backend Server                  ║
║                                                            ║
║     Server running on port ${PORT}                          ║
║     Environment: ${process.env.NODE_ENV || 'development'}                              ║
║     Default Provider: ${process.env.DEFAULT_PAYMENT_PROVIDER || 'stripe'}                          ║
║                                                            ║
║     API Documentation:                                     ║
║     - Payments: http://localhost:${PORT}/api/payments          ║
║     - Webhooks: http://localhost:${PORT}/api/webhooks          ║
║                                                            ║
║     Webhook URLs (configure in payment providers):        ║
║     - Stripe: http://localhost:${PORT}/api/webhooks/stripe    ║
║     - PayPal: http://localhost:${PORT}/api/webhooks/paypal    ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
  `);

  // Validate payment provider configurations on startup
  console.log('\nValidating payment provider configurations...\n');

  const providers = paymentService.getSupportedProviders();
  providers.forEach(provider => {
    const validation = paymentService.validateProviderConfig(provider);
    if (validation.valid) {
      console.log(`✓ ${provider.toUpperCase()}: Configured correctly`);
    } else {
      console.log(`✗ ${provider.toUpperCase()}: Configuration issues`);
      validation.errors.forEach(error => {
        console.log(`  - ${error}`);
      });
    }
  });

  console.log('\n');
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  console.log(`\nReceived ${signal}, closing server gracefully...`);

  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });

  // Force close after 10 seconds
  setTimeout(() => {
    console.error('Could not close connections in time, forcefully shutting down');
    process.exit(1);
  }, 10000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  gracefulShutdown('uncaughtException');
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

export default app; // For testing
