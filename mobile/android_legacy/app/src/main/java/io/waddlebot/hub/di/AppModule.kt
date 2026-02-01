package io.waddlebot.hub.di

import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    // Network-related providers moved to NetworkModule
    // Preferences-related providers handled by PreferencesRepository with @Inject
    // AuthRepository uses @Inject constructor, no provider needed
}
