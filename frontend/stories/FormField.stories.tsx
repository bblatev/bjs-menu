import type { Meta, StoryObj } from '@storybook/react';
import { FormField, Input, Select, Textarea, Checkbox } from '../components/ui/FormField';

const meta: Meta<typeof Input> = {
  title: 'UI/FormField',
  component: Input,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
};

export default meta;

export const BasicInput: StoryObj<typeof Input> = {
  render: () => (
    <div style={{ width: '300px' }}>
      <FormField label="Username" name="username" required>
        <Input name="username" placeholder="Enter username" />
      </FormField>
    </div>
  ),
};

export const InputWithError: StoryObj<typeof Input> = {
  render: () => (
    <div style={{ width: '300px' }}>
      <FormField label="Email" name="email" error="Please enter a valid email" touched required>
        <Input name="email" error="Please enter a valid email" touched value="invalid-email" />
      </FormField>
    </div>
  ),
};

export const InputWithHelpText: StoryObj<typeof Input> = {
  render: () => (
    <div style={{ width: '300px' }}>
      <FormField label="Password" name="password" helpText="Must be at least 8 characters">
        <Input name="password" type="password" placeholder="Enter password" />
      </FormField>
    </div>
  ),
};

export const BasicSelect: StoryObj<typeof Select> = {
  render: () => (
    <div style={{ width: '300px' }}>
      <FormField label="Country" name="country" required>
        <Select
          name="country"
          placeholder="Select a country"
          options={[
            { value: 'us', label: 'United States' },
            { value: 'uk', label: 'United Kingdom' },
            { value: 'ca', label: 'Canada' },
            { value: 'au', label: 'Australia' },
          ]}
        />
      </FormField>
    </div>
  ),
};

export const BasicTextarea: StoryObj<typeof Textarea> = {
  render: () => (
    <div style={{ width: '300px' }}>
      <FormField label="Description" name="description">
        <Textarea name="description" placeholder="Enter a description..." />
      </FormField>
    </div>
  ),
};

export const BasicCheckbox: StoryObj<typeof Checkbox> = {
  render: () => (
    <div style={{ width: '300px' }}>
      <Checkbox name="terms" label="I agree to the terms and conditions" />
    </div>
  ),
};

export const CompleteForm: StoryObj<typeof Input> = {
  render: () => (
    <div style={{ width: '400px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <FormField label="Full Name" name="name" required>
        <Input name="name" placeholder="John Doe" />
      </FormField>

      <FormField label="Email" name="email" required>
        <Input name="email" type="email" placeholder="john@example.com" />
      </FormField>

      <FormField label="Role" name="role" required>
        <Select
          name="role"
          placeholder="Select a role"
          options={[
            { value: 'admin', label: 'Administrator' },
            { value: 'manager', label: 'Manager' },
            { value: 'staff', label: 'Staff' },
          ]}
        />
      </FormField>

      <FormField label="Bio" name="bio">
        <Textarea name="bio" placeholder="Tell us about yourself..." />
      </FormField>

      <Checkbox name="active" label="Active user" />
    </div>
  ),
};
