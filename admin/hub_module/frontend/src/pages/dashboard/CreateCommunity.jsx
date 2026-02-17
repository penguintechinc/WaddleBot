import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { communityApi } from '../../services/api';
import CommunityForm from '../../components/CommunityForm';

function CreateCommunity() {
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
      const payload = {
        name: formData.name,
        displayName: formData.displayName,
        description: formData.description,
        platform: formData.platform,
        platformServerId: formData.platformServerId,
        isPublic: formData.isPublic,
        communityType: formData.communityType,
      };
      const response = await communityApi.create(payload);
      if (response.data.success) {
        const communityId = response.data.community.id;
        navigate(`/dashboard/community/${communityId}`);
      }
    } catch (err) {
      const errData = err.response?.data;
      const errMsg = errData?.error?.message || errData?.message || (typeof errData?.error === 'string' ? errData.error : null) || err.message || 'Failed to create community';
      setError(errMsg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <CommunityForm
      onSubmit={handleSubmit}
      saving={saving}
      error={error}
      showOwnerFields={false}
      backLink="/communities"
    />
  );
}

export default CreateCommunity;
