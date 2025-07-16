package com.waddlebot.premium.presentation.license

import androidx.lifecycle.ViewModel
import com.waddlebot.premium.data.repository.PreferencesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class PremiumLicenseViewModel @Inject constructor(
    private val preferencesRepository: PreferencesRepository
) : ViewModel() {
    
    fun acceptLicense() {
        preferencesRepository.setLicenseAccepted(true)
    }
    
    fun isLicenseAccepted(): Boolean {
        return preferencesRepository.isLicenseAccepted()
    }
}