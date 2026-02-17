import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { superAdminApi } from '../../services/api';
import CommunityForm from '../../components/CommunityForm';

function SuperAdminCreateCommunity() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (formData) => {
    setError(null);

    if (!formData.name.trim()) {
      setError('Community name is required');
      return;
    }

    try {
      setSaving(true);
      // Convert camelCase to snake_case for backend API
      const payload = {
        name: formData.name,
        display_name: formData.displayName,
        description: formData.description,
        platform: formData.platform,
        platform_server_id: formData.platformServerId,
        owner_id: formData.ownerId,
        owner_name: formData.ownerName,
        is_public: formData.isPublic,
        community_type: formData.communityType,
      };
      const response = await superAdminApi.createCommunity(payload);
      if (response.data.success) {
        navigate('/superadmin/communities');
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to create community');
    } finally {
      setSaving(false);
    }
  };

  return (
    <CommunityForm
      onSubmit={handleSubmit}
      saving={saving}
      error={error}
      showOwnerFields={true}
      backLink="/superadmin/communities"
    />
  );
}

export default SuperAdminCreateCommunity;
