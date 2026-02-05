package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"waddlebot-bridge/internal/auth"
	"waddlebot-bridge/internal/bridge"
	"waddlebot-bridge/internal/config"
	"waddlebot-bridge/internal/gateway"
	"waddlebot-bridge/internal/license"
	"waddlebot-bridge/internal/logger"
	"waddlebot-bridge/internal/modules"
	"waddlebot-bridge/internal/obs"
	"waddlebot-bridge/internal/poller"
	"waddlebot-bridge/internal/scripting"
	"waddlebot-bridge/internal/server"
	"waddlebot-bridge/internal/storage"
)

var (
	version = "1.0.0"
	cfgFile string
)

var rootCmd = &cobra.Command{
	Use:     "waddlebot-bridge",
	Short:   "Waddles Premium Desktop Bridge",
	Long:    `Waddles Premium Desktop Bridge - Connect your local system to Waddles communities`,
	Version: version,
	Run:     runBridge,
}

func init() {
	cobra.OnInitialize(initConfig)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.waddlebot-bridge.yaml)")
	rootCmd.PersistentFlags().String("api-url", "https://api.waddlebot.io", "Waddles API URL")
	rootCmd.PersistentFlags().String("community-id", "", "Community ID to connect to")
	rootCmd.PersistentFlags().String("user-id", "", "User ID for authentication")
	rootCmd.PersistentFlags().Int("poll-interval", 30, "Polling interval in seconds (minimum 5)")
	rootCmd.PersistentFlags().String("log-level", "info", "Log level (debug, info, warn, error)")
	rootCmd.PersistentFlags().String("data-dir", "", "Data directory for storage (default: $HOME/.waddlebot-bridge)")
	
	viper.BindPFlag("api-url", rootCmd.PersistentFlags().Lookup("api-url"))
	viper.BindPFlag("community-id", rootCmd.PersistentFlags().Lookup("community-id"))
	viper.BindPFlag("user-id", rootCmd.PersistentFlags().Lookup("user-id"))
	viper.BindPFlag("poll-interval", rootCmd.PersistentFlags().Lookup("poll-interval"))
	viper.BindPFlag("log-level", rootCmd.PersistentFlags().Lookup("log-level"))
	viper.BindPFlag("data-dir", rootCmd.PersistentFlags().Lookup("data-dir"))
}

func initConfig() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		home, err := os.UserHomeDir()
		if err != nil {
			log.Fatal(err)
		}
		viper.AddConfigPath(home)
		viper.SetConfigType("yaml")
		viper.SetConfigName(".waddlebot-bridge")
	}

	viper.AutomaticEnv()
	viper.ReadInConfig()
}

func runBridge(cmd *cobra.Command, args []string) {
	// Initialize logger
	logger.Init(viper.GetString("log-level"))
	log := logger.GetLogger()

	// Display banner
	displayBanner()

	// Check premium license
	if !license.ValidateLicense() {
		log.Fatal("Invalid or missing premium license. Please ensure you have a valid Waddles Premium subscription.")
	}

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.WithError(err).Fatal("Failed to load configuration")
	}

	// Validate required configuration
	if cfg.CommunityID == "" {
		log.Fatal("Community ID is required. Use --community-id flag or set in config file.")
	}
	if cfg.UserID == "" {
		log.Fatal("User ID is required. Use --user-id flag or set in config file.")
	}

	// Validate poll interval
	if cfg.PollInterval < 5 {
		log.Warn("Poll interval cannot be less than 5 seconds. Setting to 5 seconds.")
		cfg.PollInterval = 5
	}

	// Initialize storage
	store, err := storage.NewBoltStorage(cfg.DataDir)
	if err != nil {
		log.WithError(err).Fatal("Failed to initialize storage")
	}
	defer store.Close()

	// Initialize WebAuthn authenticator
	authenticator, err := auth.NewWebAuthnManager(cfg, store)
	if err != nil {
		log.WithError(err).Fatal("Failed to initialize WebAuthn")
	}

	// Initialize module manager
	moduleManager := modules.NewManager(cfg, store)

	// Initialize OBS client if enabled
	var obsClient *obs.Client
	if cfg.OBS.Enabled {
		obsConfig := obs.Config{
			Host:                 cfg.OBS.Host,
			Port:                 cfg.OBS.Port,
			Password:             cfg.OBS.Password,
			AutoReconnect:        cfg.OBS.AutoReconnect,
			ReconnectInterval:    cfg.OBS.ReconnectInterval,
			MaxReconnectInterval: cfg.OBS.MaxReconnectInterval,
			Timeout:              cfg.OBS.Timeout,
			Enabled:              cfg.OBS.Enabled,
		}
		obsClient = obs.NewClient(obsConfig, log)
		log.Info("OBS integration enabled")
	}

	// Initialize scripting manager if enabled
	var scriptManager *scripting.Manager
	if cfg.Scripting.Enabled {
		scriptManager, err = scripting.NewManager(cfg.Scripting, log)
		if err != nil {
			log.WithError(err).Warn("Failed to initialize scripting manager")
		} else {
			log.WithField("engines", scriptManager.GetEnabledTypes()).Info("Scripting engine initialized")
		}
	}

	// Initialize bridge client
	bridgeClient, err := bridge.NewClient(cfg, authenticator, moduleManager)
	if err != nil {
		log.WithError(err).Fatal("Failed to initialize bridge client")
	}

	// Initialize poller
	pollerInstance := poller.NewPoller(cfg, bridgeClient, moduleManager)

	// Initialize web server for WebAuthn
	webServer := server.NewWebServer(cfg, authenticator, bridgeClient)

	// Initialize local API gateway if enabled
	var gatewayServer *gateway.Gateway
	if cfg.Gateway.Enabled {
		gatewayServer = gateway.New(cfg.Gateway, obsClient, log)
		log.WithFields(map[string]interface{}{
			"host": cfg.Gateway.Host,
			"port": cfg.Gateway.Port,
		}).Info("Local API gateway enabled")
	}

	// Create context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle signals for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start components
	log.Info("Starting Waddles Premium Desktop Bridge...")

	// Start OBS client if enabled
	if obsClient != nil {
		go func() {
			if err := obsClient.Connect(ctx); err != nil {
				log.WithError(err).Warn("OBS connection failed - will retry automatically")
			} else {
				log.Info("Connected to OBS Studio")
				// Start event listener
				if err := obsClient.StartEventListener(); err != nil {
					log.WithError(err).Error("Failed to start OBS event listener")
				}
			}
		}()
	}

	// Start local API gateway if enabled
	if gatewayServer != nil {
		go func() {
			if err := gatewayServer.Start(ctx); err != nil {
				log.WithError(err).Error("Gateway server error")
			}
		}()
	}

	// Start web server
	go func() {
		if err := webServer.Start(ctx); err != nil {
			log.WithError(err).Error("Web server error")
		}
	}()

	// Start poller
	go func() {
		if err := pollerInstance.Start(ctx); err != nil {
			log.WithError(err).Error("Poller error")
		}
	}()

	// Display connection info
	connectionInfo := map[string]interface{}{
		"community_id":  cfg.CommunityID,
		"user_id":       cfg.UserID,
		"poll_interval": cfg.PollInterval,
		"api_url":       cfg.APIURL,
		"web_port":      cfg.WebPort,
	}

	if cfg.OBS.Enabled {
		connectionInfo["obs_enabled"] = true
		connectionInfo["obs_host"] = cfg.OBS.Host
		connectionInfo["obs_port"] = cfg.OBS.Port
	}

	if cfg.Gateway.Enabled {
		connectionInfo["gateway_enabled"] = true
		connectionInfo["gateway_port"] = cfg.Gateway.Port
	}

	if cfg.Scripting.Enabled && scriptManager != nil {
		connectionInfo["scripting_enabled"] = true
		connectionInfo["script_engines"] = scriptManager.GetEnabledTypes()
	}

	log.WithFields(connectionInfo).Info("Bridge initialized successfully")

	// Wait for shutdown signal
	<-sigChan
	log.Info("Shutting down Waddles Bridge...")

	// Cancel context to stop all components
	cancel()

	// Shutdown OBS client
	if obsClient != nil {
		if err := obsClient.Disconnect(); err != nil {
			log.WithError(err).Warn("Error disconnecting from OBS")
		} else {
			log.Info("Disconnected from OBS Studio")
		}
	}

	// Shutdown gateway server
	if gatewayServer != nil {
		if err := gatewayServer.Stop(); err != nil {
			log.WithError(err).Warn("Error stopping gateway server")
		} else {
			log.Info("Gateway server stopped")
		}
	}

	// Give components time to shutdown gracefully
	time.Sleep(2 * time.Second)
	log.Info("Waddles Bridge stopped")
}

func displayBanner() {
	fmt.Println(`
██╗    ██╗ █████╗ ██████╗ ██████╗ ██╗     ███████╗██████╗  ██████╗ ████████╗
██║    ██║██╔══██╗██╔══██╗██╔══██╗██║     ██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝
██║ █╗ ██║███████║██║  ██║██║  ██║██║     █████╗  ██████╔╝██║   ██║   ██║   
██║███╗██║██╔══██║██║  ██║██║  ██║██║     ██╔══╝  ██╔══██╗██║   ██║   ██║   
╚███╔███╔╝██║  ██║██████╔╝██████╔╝███████╗███████╗██████╔╝╚██████╔╝   ██║   
 ╚══╝╚══╝ ╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚═════╝  ╚═════╝    ╚═╝   
                                                                              
                    Premium Desktop Bridge v` + version + `
                    Local System Integration Platform
`)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		log.Fatal(err)
	}
}