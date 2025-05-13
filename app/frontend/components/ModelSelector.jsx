import React, { useState, useEffect } from 'react';
import { 
  Box, 
  FormControl, 
  FormLabel, 
  Select, 
  Button, 
  VStack, 
  HStack, 
  Text,
  Heading,
  Divider,
  useToast,
  Badge,
  Card,
  CardBody,
  Spinner
} from '@chakra-ui/react';

/**
 * ModelSelector component for selecting primary and secondary LLM models
 */
const ModelSelector = () => {
  // State for available models
  const [availableModels, setAvailableModels] = useState({
    openai_models: [],
    google_models: [],
    llama_models: []
  });
  
  // State for selected models
  const [primaryModel, setPrimaryModel] = useState('');
  const [secondaryModel, setSecondaryModel] = useState('');
  
  // Loading state
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  
  // Toast for notifications
  const toast = useToast();
  
  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoading(true);
        const response = await fetch('/api/models/available');
        
        if (!response.ok) {
          throw new Error('Failed to fetch available models');
        }
        
        const data = await response.json();
        setAvailableModels(data);
        
        // Set defaults from the first available models
        if (data.openai_models.length > 0 && !primaryModel) {
          setPrimaryModel(data.openai_models[0].name);
        }
        
        if (data.google_models.length > 0 && !secondaryModel) {
          setSecondaryModel(data.google_models[0].name);
        }
      } catch (error) {
        console.error('Error fetching models:', error);
        toast({
          title: 'Error fetching models',
          description: error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchModels();
  }, []);
  
  // Handle saving model selections
  const handleSaveSelection = async () => {
    try {
      setIsSaving(true);
      
      const response = await fetch('/api/models/select', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          primary_model: primaryModel,
          secondary_model: secondaryModel,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to save model selection');
      }
      
      const data = await response.json();
      
      toast({
        title: 'Models updated',
        description: 'Your model selections have been saved.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error saving model selection:', error);
      toast({
        title: 'Error saving models',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSaving(false);
    }
  };
  
  // Get provider color based on provider name
  const getProviderColor = (provider) => {
    switch (provider.toLowerCase()) {
      case 'openai':
        return 'green';
      case 'google':
        return 'blue';
      case 'meta':
        return 'purple';
      default:
        return 'gray';
    }
  };
  
  // Find model description by name
  const getModelDescription = (modelName) => {
    // Search through all provider's models
    for (const provider of ['openai_models', 'google_models', 'llama_models']) {
      const model = availableModels[provider].find(m => m.name === modelName);
      if (model) {
        return model.description;
      }
    }
    return '';
  };
  
  // Find model provider by name
  const getModelProvider = (modelName) => {
    // Search through all provider's models
    for (const provider of ['openai_models', 'google_models', 'llama_models']) {
      const model = availableModels[provider].find(m => m.name === modelName);
      if (model) {
        return model.provider;
      }
    }
    return '';
  };
  
  if (isLoading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Loading available models...</Text>
      </Box>
    );
  }
  
  return (
    <Card variant="outline" my={4}>
      <CardBody>
        <Heading size="md" mb={4}>Model Selection</Heading>
        <Text mb={4}>
          Select the LLM models to use for different tasks in the research assistant.
        </Text>
        
        <Divider my={4} />
        
        <VStack spacing={6} align="stretch">
          {/* Primary Model Selection */}
          <Box>
            <FormControl id="primary-model">
              <FormLabel fontWeight="bold">
                Primary Model (for planning and complex tasks)
              </FormLabel>
              <Select 
                value={primaryModel}
                onChange={(e) => setPrimaryModel(e.target.value)}
              >
                <optgroup label="OpenAI Models">
                  {availableModels.openai_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Google Models">
                  {availableModels.google_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Meta Llama Models">
                  {availableModels.llama_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </optgroup>
              </Select>
            </FormControl>
            
            {primaryModel && (
              <Box mt={2}>
                <HStack>
                  <Badge colorScheme={getProviderColor(getModelProvider(primaryModel))}>
                    {getModelProvider(primaryModel)}
                  </Badge>
                  <Text fontSize="sm" color="gray.600">
                    {getModelDescription(primaryModel)}
                  </Text>
                </HStack>
              </Box>
            )}
          </Box>
          
          {/* Secondary Model Selection */}
          <Box>
            <FormControl id="secondary-model">
              <FormLabel fontWeight="bold">
                Secondary Model (for simpler agent steps)
              </FormLabel>
              <Select 
                value={secondaryModel}
                onChange={(e) => setSecondaryModel(e.target.value)}
              >
                <optgroup label="OpenAI Models">
                  {availableModels.openai_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Google Models">
                  {availableModels.google_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Meta Llama Models">
                  {availableModels.llama_models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                </optgroup>
              </Select>
            </FormControl>
            
            {secondaryModel && (
              <Box mt={2}>
                <HStack>
                  <Badge colorScheme={getProviderColor(getModelProvider(secondaryModel))}>
                    {getModelProvider(secondaryModel)}
                  </Badge>
                  <Text fontSize="sm" color="gray.600">
                    {getModelDescription(secondaryModel)}
                  </Text>
                </HStack>
              </Box>
            )}
          </Box>
        </VStack>
        
        <Divider my={4} />
        
        <Box textAlign="right">
          <Button 
            colorScheme="blue" 
            onClick={handleSaveSelection}
            isLoading={isSaving}
            loadingText="Saving"
          >
            Save Model Selection
          </Button>
        </Box>
      </CardBody>
    </Card>
  );
};

export default ModelSelector; 