package com.waddlebot.premium.data.repository

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "waddlebot_preferences")

@Singleton
class PreferencesRepository @Inject constructor(
    @ApplicationContext private val context: Context
) {
    companion object {
        private val LICENSE_ACCEPTED_KEY = booleanPreferencesKey("license_accepted")
        private val USER_TOKEN_KEY = stringPreferencesKey("user_token")
        private val REFRESH_TOKEN_KEY = stringPreferencesKey("refresh_token")
        private val USER_DATA_KEY = stringPreferencesKey("user_data")
        private val PREMIUM_STATUS_KEY = booleanPreferencesKey("premium_status")
    }
    
    // License acceptance
    fun setLicenseAccepted(accepted: Boolean) {
        runBlocking {
            context.dataStore.edit { preferences ->
                preferences[LICENSE_ACCEPTED_KEY] = accepted
            }
        }
    }
    
    fun isLicenseAccepted(): Boolean {
        return runBlocking {
            context.dataStore.data.first()[LICENSE_ACCEPTED_KEY] ?: false
        }
    }
    
    // Authentication tokens
    suspend fun saveUserToken(token: String) {
        context.dataStore.edit { preferences ->
            preferences[USER_TOKEN_KEY] = token
        }
    }
    
    fun getUserToken(): Flow<String?> {
        return context.dataStore.data.map { preferences ->
            preferences[USER_TOKEN_KEY]
        }
    }
    
    suspend fun saveRefreshToken(token: String) {
        context.dataStore.edit { preferences ->
            preferences[REFRESH_TOKEN_KEY] = token
        }
    }
    
    fun getRefreshToken(): Flow<String?> {
        return context.dataStore.data.map { preferences ->
            preferences[REFRESH_TOKEN_KEY]
        }
    }
    
    // User data
    suspend fun saveUserData(userData: String) {
        context.dataStore.edit { preferences ->
            preferences[USER_DATA_KEY] = userData
        }
    }
    
    fun getUserData(): Flow<String?> {
        return context.dataStore.data.map { preferences ->
            preferences[USER_DATA_KEY]
        }
    }
    
    // Premium status
    suspend fun savePremiumStatus(isPremium: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[PREMIUM_STATUS_KEY] = isPremium
        }
    }
    
    fun getPremiumStatus(): Flow<Boolean> {
        return context.dataStore.data.map { preferences ->
            preferences[PREMIUM_STATUS_KEY] ?: false
        }
    }
    
    // Clear all data
    suspend fun clearAllData() {
        context.dataStore.edit { preferences ->
            preferences.clear()
        }
    }
}