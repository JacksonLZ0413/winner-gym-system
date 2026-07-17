const app = getApp()

Page({
  data: {
    username: '',
    name: '',
    phone: '',
    password: '',
    confirmPassword: '',
    loading: false
  },

  onUsernameInput: function(e) {
    this.setData({
      username: e.detail.value
    })
  },

  onNameInput: function(e) {
    this.setData({
      name: e.detail.value
    })
  },

  onPhoneInput: function(e) {
    this.setData({
      phone: e.detail.value
    })
  },

  onPasswordInput: function(e) {
    this.setData({
      password: e.detail.value
    })
  },

  onConfirmPasswordInput: function(e) {
    this.setData({
      confirmPassword: e.detail.value
    })
  },

  doRegister: function() {
    const { username, name, phone, password, confirmPassword } = this.data
    
    if (!username || !name || !password) {
      wx.showToast({ title: '请填写完整信息', icon: 'none' })
      return
    }
    
    if (password.length < 6) {
      wx.showToast({ title: '密码至少6位', icon: 'none' })
      return
    }
    
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    
    app.request({
      url: '/register',
      method: 'POST',
      data: { username, name, phone, password },
      noAuth: true
    }).then((data) => {
      app.globalData.token = data.token
      app.globalData.userInfo = data.user
      wx.setStorageSync('token', data.token)
      wx.setStorageSync('userInfo', data.user)
      wx.showToast({ title: '注册成功', icon: 'success' })
      setTimeout(() => {
        wx.switchTab({
          url: '/pages/my/my'
        })
      }, 1500)
    }).catch((err) => {
      wx.showToast({ title: err, icon: 'none' })
    }).finally(() => {
      this.setData({ loading: false })
    })
  },

  goToLogin: function() {
    wx.navigateBack()
  }
})
